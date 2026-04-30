#!/usr/bin/env python3
"""validate-example-policy.py — enforce +kubebuilder:example= marker policy.

Single source of truth for the policy is the FIELD_CASE_RULES and
ENUM_DEFINITION_RULE tables below. To change the policy, edit those
tables; the classifier and runner do not need to change.

Usage:
  python3 scripts/validate-example-policy.py           # report, exit 0
  python3 scripts/validate-example-policy.py --strict  # exit 1 on violation
  python3 scripts/validate-example-policy.py --format json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field as dc_field
from typing import Optional


# ─── Policy ────────────────────────────────────────────────────────────
# Edit these two tables to change the policy. Case keys must match
# classify_case() outputs.

FIELD_CASE_RULES = {
    "single scalar":     {"id": "R1",  "field_example": "required"},
    "repeated scalar":   {"id": "R2",  "field_example": "required", "min_array_elements": 2},
    "single our-enum":   {"id": "R3a", "field_example": "required"},
    "repeated our-enum": {"id": "R4",  "field_example": "required", "min_array_elements": 2},
    "single our-msg":    {"id": "R5",  "field_example": "forbidden"},
    "repeated our-msg":  {"id": "R6",  "field_example": "forbidden"},
    "single external":   {"id": "R7",  "field_example": "required"},
    "repeated external": {"id": "R8",  "field_example": "required", "allow_empty_array": True},
    "map":               {"id": "R9",  "field_example": "required"},
}

ENUM_DEFINITION_RULE = {"id": "R3b", "def_level_example": "forbidden"}

DEFAULT_SCOPE_GLOBS = ["coreapi/model/*.proto", "coreapi/common/*.proto"]

PROTO_SCALARS = {
    "string", "int32", "int64", "uint32", "uint64", "sint32", "sint64",
    "fixed32", "fixed64", "sfixed32", "sfixed64", "float", "double", "bool", "bytes",
}


# ─── Data model ────────────────────────────────────────────────────────

@dataclass
class Location:
    file: str
    line: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class Field:
    loc: Location
    name: str
    proto_type: str
    qualifier: Optional[str] = None
    is_map: bool = False
    map_key_type: Optional[str] = None
    map_value_type: Optional[str] = None
    example_raw: Optional[str] = None

    @property
    def is_repeated(self) -> bool:
        return self.qualifier == "repeated"

    @property
    def has_example(self) -> bool:
        return self.example_raw is not None


@dataclass
class EnumDefinition:
    loc: Location
    name: str
    example_raw: Optional[str] = None


@dataclass
class Violation:
    rule_id: str
    loc: Location
    case: str
    message: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "file": self.loc.file,
            "line": self.loc.line,
            "case": self.case,
            "message": self.message,
        }


# ─── Parsing ───────────────────────────────────────────────────────────

_MAP_FIELD_RE = re.compile(r"^\s*(map<\s*([^,>\s]+)\s*,\s*([^>]+)>)\s+(\w+)\s*=\s*\d+")
_FIELD_RE = re.compile(r"^\s*(?:(repeated|optional)\s+)?([a-zA-Z_][\w.]*)\s+(\w+)\s*=\s*\d+")
_ENUM_RE = re.compile(r"^\s*enum\s+(\w+)\s*\{")
_MESSAGE_RE = re.compile(r"^\s*message\s+(\w+)\s*\{")
_EXAMPLE_MARKER_RE = re.compile(r"kubebuilder:example=(.+?)\s*$")
_NON_FIELD_KEYWORDS = {"option", "syntax", "package", "import", "reserved", "extensions"}
_MAX_COMMENT_LOOKBACK = 8


def _preceding_example(lines: list[str], idx: int) -> Optional[str]:
    for j in range(idx - 1, max(-1, idx - 1 - _MAX_COMMENT_LOOKBACK), -1):
        if j < 0:
            break
        s = lines[j].strip()
        if not s:
            break
        if not s.startswith("//"):
            break
        m = _EXAMPLE_MARKER_RE.search(lines[j])
        if m:
            return m.group(1).strip()
    return None


def build_type_universe(files: list[pathlib.Path]) -> tuple[set[str], set[str]]:
    our_enums: set[str] = set()
    our_messages: set[str] = set()
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            m = _ENUM_RE.match(line)
            if m:
                our_enums.add(m.group(1))
                continue
            m = _MESSAGE_RE.match(line)
            if m:
                our_messages.add(m.group(1))
    return our_enums, our_messages


def parse_file(path: pathlib.Path) -> tuple[list[Field], list[EnumDefinition]]:
    fields: list[Field] = []
    enum_defs: list[EnumDefinition] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    for i, line in enumerate(lines):
        loc = Location(str(path), i + 1)

        m = _MAP_FIELD_RE.match(line)
        if m:
            fields.append(Field(
                loc=loc,
                name=m.group(4),
                proto_type=m.group(1),
                is_map=True,
                map_key_type=m.group(2).strip(),
                map_value_type=m.group(3).strip(),
                example_raw=_preceding_example(lines, i),
            ))
            continue

        m = _ENUM_RE.match(line)
        if m:
            enum_defs.append(EnumDefinition(
                loc=loc,
                name=m.group(1),
                example_raw=_preceding_example(lines, i),
            ))
            continue

        if _MESSAGE_RE.match(line):
            continue

        m = _FIELD_RE.match(line)
        if m:
            qualifier = m.group(1)
            if qualifier == "optional":
                qualifier = None
            type_tok = m.group(2)
            if type_tok in _NON_FIELD_KEYWORDS:
                continue
            fields.append(Field(
                loc=loc,
                name=m.group(3),
                proto_type=type_tok,
                qualifier=qualifier,
                example_raw=_preceding_example(lines, i),
            ))

    return fields, enum_defs


# ─── Classification ────────────────────────────────────────────────────

def classify_type(type_token: str, our_enums: set[str], our_messages: set[str]) -> str:
    if type_token in PROTO_SCALARS:
        return "scalar"
    if type_token.startswith("google.protobuf."):
        return "external"
    simple = type_token.split(".")[-1]
    if simple in our_enums:
        return "our-enum"
    if simple in our_messages:
        return "our-msg"
    return "unknown"


def classify_case(f: Field, our_enums: set[str], our_messages: set[str]) -> Optional[str]:
    if f.is_map:
        return "map"
    kind = classify_type(f.proto_type, our_enums, our_messages)
    if kind == "unknown":
        return None
    return f"{'repeated' if f.is_repeated else 'single'} {kind}"


# ─── Checking ──────────────────────────────────────────────────────────

def _array_element_count(raw: str) -> Optional[int]:
    try:
        val = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return len(val) if isinstance(val, list) else None


_FORBIDDEN_REASON = {
    "single our-msg": "internal fields propagate via $ref; remove this marker",
    "repeated our-msg": "items $ref auto-composes; remove this marker",
}


def check_field(f: Field, our_enums: set[str], our_messages: set[str]) -> list[Violation]:
    case = classify_case(f, our_enums, our_messages)
    if case is None or case not in FIELD_CASE_RULES:
        return []
    rule = FIELD_CASE_RULES[case]
    rid = rule["id"]
    fx = rule.get("field_example")
    violations: list[Violation] = []

    if fx == "required" and not f.has_example:
        violations.append(Violation(
            rule_id=rid, loc=f.loc, case=case,
            message=f"{case} field '{f.name}' ({f.proto_type}) MUST have +kubebuilder:example= marker",
        ))
    elif fx == "forbidden" and f.has_example:
        reason = _FORBIDDEN_REASON.get(case, "remove this marker")
        violations.append(Violation(
            rule_id=rid, loc=f.loc, case=case,
            message=f"{case} field '{f.name}' MUST NOT have field-level example (got {f.example_raw!r}) — {reason}",
        ))

    min_elems = rule.get("min_array_elements")
    if fx == "required" and f.has_example and min_elems is not None:
        n = _array_element_count(f.example_raw)
        allow_empty = rule.get("allow_empty_array", False)
        if n is not None and not (n == 0 and allow_empty) and n < min_elems:
            violations.append(Violation(
                rule_id=rid, loc=f.loc, case=case,
                message=f"{case} field '{f.name}' example has {n} element(s); expected ≥{min_elems} to show plurality",
            ))

    return violations


def check_enum_def(e: EnumDefinition) -> list[Violation]:
    rule = ENUM_DEFINITION_RULE
    if rule["def_level_example"] == "forbidden" and e.example_raw is not None:
        return [Violation(
            rule_id=rule["id"], loc=e.loc, case="enum definition",
            message=f"enum '{e.name}' has definition-level example {e.example_raw!r} — MUST NOT "
                    f"(use per-field example on each usage site instead)",
        )]
    return []


# ─── Runner ────────────────────────────────────────────────────────────

def collect_files(repo_root: pathlib.Path, globs: list[str]) -> list[pathlib.Path]:
    result: list[pathlib.Path] = []
    for g in globs:
        result.extend(repo_root.glob(g))
    return sorted(set(result))


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate +kubebuilder:example= marker policy")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any violation (default: exit 0 with report)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--repo-root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    files = collect_files(repo_root, DEFAULT_SCOPE_GLOBS)
    if not files:
        print(f"error: no proto files matched {DEFAULT_SCOPE_GLOBS} under {repo_root}", file=sys.stderr)
        return 2

    our_enums, our_messages = build_type_universe(files)

    violations: list[Violation] = []
    fields_total = 0
    enum_defs_total = 0
    for path in files:
        rel = path.relative_to(repo_root)
        fields, enum_defs = parse_file(path)
        for item in (*fields, *enum_defs):
            item.loc = Location(str(rel), item.loc.line)
        fields_total += len(fields)
        enum_defs_total += len(enum_defs)
        for f in fields:
            violations.extend(check_field(f, our_enums, our_messages))
        for e in enum_defs:
            violations.extend(check_enum_def(e))

    violations.sort(key=lambda v: (v.loc.file, v.loc.line, v.rule_id))

    if args.format == "json":
        print(json.dumps({
            "scope": DEFAULT_SCOPE_GLOBS,
            "files_scanned": len(files),
            "fields_scanned": fields_total,
            "enum_defs_scanned": enum_defs_total,
            "violation_count": len(violations),
            "violations": [v.to_dict() for v in violations],
        }, indent=2, ensure_ascii=False))
    else:
        for v in violations:
            print(f"{v.loc} [{v.rule_id}] {v.message}")
        print()
        print(f"Scope:   {', '.join(DEFAULT_SCOPE_GLOBS)}")
        print(f"Scanned: {len(files)} files, {fields_total} fields, {enum_defs_total} enum definitions")
        print(f"Violations: {len(violations)}")
        if violations:
            print("\nBy rule:")
            for rid, n in sorted(Counter(v.rule_id for v in violations).items()):
                print(f"  {rid}: {n}")

    return 1 if args.strict and violations else 0


if __name__ == "__main__":
    sys.exit(main())
