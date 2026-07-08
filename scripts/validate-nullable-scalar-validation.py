#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# --- How to run ---
# Run from the repository root:
#   python3 scripts/validate-nullable-scalar-validation.py
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterator


ROOT: Final = Path(__file__).resolve().parents[1]
RULE_ID: Final = "nullable_plain_scalar"
PROTO_DIRS: Final = ("coreapi/service", "coreapi/model", "coreapi/common")
STRING_FIELD_RE: Final = re.compile(r"^\s*string\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")
STRING_PATTERN_RE: Final = re.compile(
    r'\(buf\.validate\.field\)\.string\.pattern\s*=\s*"((?:\\.|[^"])*)"'
)


@dataclass(frozen=True)
class FieldBlock:
    path: Path
    line: int
    comments: str
    body: str


def main() -> int:
    violations = collect_violations()
    if violations:
        for violation in violations:
            print(violation)
        print(f"validate-nullable-scalar-validation: {len(violations)} error(s) found")
        return 1

    print("validate-nullable-scalar-validation: ok")
    return 0


def collect_violations() -> list[str]:
    violations: list[str] = []
    for proto_file in iter_proto_files():
        for field in iter_field_blocks(proto_file):
            violation = check_nullable_string_field(field)
            if violation is not None:
                violations.append(violation)
    return violations


def iter_proto_files() -> Iterator[Path]:
    for proto_dir in PROTO_DIRS:
        yield from sorted((ROOT / proto_dir).glob("*.proto"))


def iter_field_blocks(path: Path) -> Iterator[FieldBlock]:
    lines = path.read_text(encoding="utf-8").splitlines()
    comments: list[str] = []
    comment_start = 0
    index = 0

    while index < len(lines):
        line = lines[index]
        line_number = index + 1

        if line.lstrip().startswith("//"):
            if not comments:
                comment_start = line_number
            comments.append(line)
            index += 1
            continue

        if comments and line.strip():
            field_lines = [line]
            while ";" not in field_lines[-1] and index + 1 < len(lines):
                index += 1
                field_lines.append(lines[index])
            yield FieldBlock(
                path=path,
                line=comment_start,
                comments="\n".join(comments),
                body="\n".join(field_lines),
            )

        comments = []
        comment_start = 0
        index += 1


def check_nullable_string_field(field: FieldBlock) -> str | None:
    if "+kubebuilder:validation:Nullable" not in field.comments:
        return None
    if STRING_FIELD_RE.search(field.body) is None:
        return None
    if "(buf.validate.field).ignore_empty = true" in field.body:
        return None

    if "+kubebuilder:validation:MinLength=" in field.comments and not has_empty_guard(field.body):
        return format_violation(field, "nullable string MinLength validation must allow empty proto3 default")

    if "+kubebuilder:validation:Pattern=" not in field.comments:
        return None

    pattern_match = STRING_PATTERN_RE.search(field.body)
    if pattern_match is None:
        if has_empty_guard(field.body):
            return None
        return format_violation(field, "nullable string Pattern validation must allow empty proto3 default")

    raw_pattern = pattern_match.group(1)
    if pattern_allows_empty(raw_pattern):
        return None
    return format_violation(field, "nullable string pattern must match empty proto3 default")


def has_empty_guard(body: str) -> bool:
    return "this == ''" in body or 'this == ""' in body


def pattern_allows_empty(raw_pattern: str) -> bool:
    pattern = decode_proto_string(raw_pattern)
    try:
        return re.search(pattern, "") is not None
    except re.error:
        return raw_pattern.startswith("^$|") or "|^$" in raw_pattern


def decode_proto_string(raw_value: str) -> str:
    return bytes(raw_value, "utf-8").decode("unicode_escape")


def format_violation(field: FieldBlock, message: str) -> str:
    display_path = field.path.relative_to(ROOT)
    return f"{display_path}:{field.line}: {message}"


if __name__ == "__main__":
    sys.exit(main())
