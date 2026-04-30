#!/usr/bin/env python3
"""validate-example-output.py — enforce example coverage on generated OpenAPI yaml.

Companion to validate-example-policy.py which enforces marker existence on
proto files (FIELD_CASE_RULES). This script enforces that the yaml produced
by protoc-gen-openapi actually carries example: values for every leaf
property — catching generator drops that proto-level policy alone cannot see.

Scope: OpenAPI yaml emitted by protoc-gen-openapi with split_schemas=true
from coreapi/model/*.proto and coreapi/common/*.proto. Input is a directory
of flat *.yaml files; cross-references use `./Other.yaml` relative paths.

Policy alignment with FIELD_CASE_RULES (ch-proto-public/scripts/validate-example-policy.py):
  R1/R2/R7/R8/R9 (required): every leaf property must carry `example:`
    directly, on a $ref sibling, or transitively via oneOf/anyOf/allOf/items.
  R3a/R4 (enum usage via $ref): $ref + sibling example satisfies coverage.
  R3b (enum definition): top-level enum yaml files (enum + no properties)
    are skipped — the policy forbids definition-level examples on enum types.
  R5/R6 (structured our-msg forbidden): inline objects with their own
    `properties`, or $ref-targets that resolve to such, are recursed into
    but not counted as leaves; the nested scalar fields carry examples.

Circular degrade: array items of the form `{type: object}` with no
properties/additionalProperties/$ref indicate the generator collapsed a
self-referential message (e.g. Block.blocks -> []Block). These are
skipped — the coverage question is answered by the sibling properties.

Usage:
  python3 scripts/validate-example-output.py <yaml-dir>           # report
  python3 scripts/validate-example-output.py --strict <yaml-dir>  # exit 1 on miss
  python3 scripts/validate-example-output.py --format json <yaml-dir>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


@dataclass
class MissingField:
    path: str
    type: str
    schema: str

    def to_dict(self) -> dict:
        return {"path": self.path, "type": self.type, "schema": self.schema}


@dataclass
class SchemaStats:
    total: int = 0
    with_example: int = 0
    missing: int = 0

    def to_dict(self) -> dict:
        return {"total": self.total, "with_example": self.with_example, "missing": self.missing}


@dataclass
class Report:
    yaml_dir: str
    schema_count: int = 0
    total_visited: int = 0
    with_example: int = 0
    missing_count: int = 0
    coverage_pct: float = 0.0
    missing_fields: list[MissingField] = field(default_factory=list)
    by_schema: dict[str, SchemaStats] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "yaml_dir": self.yaml_dir,
            "schema_count": self.schema_count,
            "total_visited": self.total_visited,
            "with_example": self.with_example,
            "missing_count": self.missing_count,
            "coverage_pct": self.coverage_pct,
            "missing_fields": [m.to_dict() for m in self.missing_fields],
            "by_schema": {k: v.to_dict() for k, v in self.by_schema.items()},
        }


class Walker:
    def __init__(self, schemas: dict[str, Any]) -> None:
        self.schemas = schemas
        self.report = Report(yaml_dir="")
        self._current_schema = ""
        self._visited: set[int] = set()

    def _stat(self, name: str) -> SchemaStats:
        s = self.report.by_schema.get(name)
        if s is None:
            s = SchemaStats()
            self.report.by_schema[name] = s
        return s

    @staticmethod
    def _schema_type(sc: Any) -> str:
        if not isinstance(sc, dict):
            return ""
        t = sc.get("type")
        if isinstance(t, list):
            return "|".join(t)
        return t or ""

    @staticmethod
    def _has_example(sc: Any) -> bool:
        if not isinstance(sc, dict):
            return False
        if "example" in sc:
            return True
        for kw in ("oneOf", "anyOf", "allOf"):
            for branch in sc.get(kw, []) or []:
                if Walker._has_example(branch):
                    return True
        items = sc.get("items")
        if isinstance(items, dict) and Walker._has_example(items):
            return True
        return False

    def _resolve_ref(self, sc: dict) -> Optional[dict]:
        ref = sc.get("$ref")
        if not ref:
            return None
        if ref.startswith("./") and ref.endswith(".yaml"):
            name = ref[2:-5]
            return self.schemas.get(name)
        return None

    def walk_all(self) -> None:
        for name in sorted(self.schemas.keys()):
            sc = self.schemas[name]
            if not isinstance(sc, dict):
                continue
            self._current_schema = name
            self._stat(name)

            is_leaf = (
                not sc.get("properties")
                and not sc.get("oneOf")
                and not sc.get("anyOf")
                and not sc.get("allOf")
                and not sc.get("additionalProperties")
                and not sc.get("items")
            )
            if is_leaf:
                if sc.get("enum"):
                    continue
                self._walk_property(name, sc)
                continue
            self._walk_schema(name, sc)

    def _walk_schema(self, path: str, sc: Any) -> None:
        if not isinstance(sc, dict):
            return
        key = id(sc)
        if key in self._visited:
            return
        self._visited.add(key)
        try:
            for kw in ("oneOf", "anyOf", "allOf"):
                for i, branch in enumerate(sc.get(kw, []) or []):
                    self._walk_schema(f"{path}.{kw}[{i}]", branch)

            props = sc.get("properties")
            if isinstance(props, dict):
                for pname in sorted(props.keys()):
                    self._walk_property(f"{path}.{pname}", props[pname])

            addl = sc.get("additionalProperties")
            if isinstance(addl, dict) and addl.get("properties"):
                self._walk_property(f"{path}.<additionalProperties>", addl)

            items = sc.get("items")
            if isinstance(items, dict) and not sc.get("properties"):
                if isinstance(items, dict) and items.get("properties"):
                    self._walk_schema(f"{path}[]", items)
        finally:
            self._visited.discard(key)

    def _walk_property(self, path: str, sc: Any) -> None:
        if not isinstance(sc, dict):
            return

        resolved = sc
        if sc.get("$ref"):
            target = self._resolve_ref(sc)
            if isinstance(target, dict) and target.get("properties"):
                self._walk_schema(path, target)
                return
            if isinstance(target, dict):
                resolved = target

        if isinstance(sc, dict) and sc.get("properties"):
            self._walk_schema(path, sc)
            return

        items = sc.get("items") if isinstance(sc, dict) else None
        if isinstance(items, dict):
            items_target = items
            if items.get("$ref"):
                t = self._resolve_ref(items)
                if isinstance(t, dict):
                    items_target = t
            if items_target.get("properties"):
                self._walk_schema(f"{path}[]", items_target)
                return
            if (
                items_target.get("type") == "object"
                and not items_target.get("properties")
                and not items_target.get("additionalProperties")
                and not items_target.get("$ref")
            ):
                return

        has = self._has_example(sc)
        if not has and sc is not resolved:
            has = self._has_example(resolved)

        typ = self._schema_type(resolved)

        self.report.total_visited += 1
        stat = self._stat(self._current_schema)
        stat.total += 1
        if has:
            self.report.with_example += 1
            stat.with_example += 1
        else:
            stat.missing += 1
            self.report.missing_fields.append(
                MissingField(path=path, type=typ, schema=self._current_schema)
            )

        if isinstance(sc, dict):
            self._walk_schema(path, sc)

    def finalize(self, yaml_dir: str) -> Report:
        self.report.yaml_dir = yaml_dir
        self.report.schema_count = len(self.schemas)
        self.report.missing_count = len(self.report.missing_fields)
        if self.report.total_visited > 0:
            self.report.coverage_pct = round(
                100.0 * self.report.with_example / self.report.total_visited, 2
            )
        self.report.missing_fields.sort(key=lambda m: (m.schema, m.path))
        return self.report


def load_yaml_dir(path: pathlib.Path) -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for p in sorted(path.glob("*.yaml")):
        name = p.stem
        try:
            with p.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SystemExit(f"error: failed to parse {p}: {e}")
        if not isinstance(data, dict):
            raise SystemExit(f"error: {p} is not a yaml mapping")
        schemas[name] = data
    return schemas


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate example coverage on generated OpenAPI yaml")
    ap.add_argument("yaml_dir", help="directory containing split_schemas yaml files")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any leaf is missing an example")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--max-missing-print", type=int, default=50,
                    help="in text mode, print at most this many missing paths (default: 50)")
    args = ap.parse_args()

    yaml_dir = pathlib.Path(args.yaml_dir).resolve()
    if not yaml_dir.is_dir():
        print(f"error: yaml-dir not found: {yaml_dir}", file=sys.stderr)
        return 2

    schemas = load_yaml_dir(yaml_dir)
    if not schemas:
        print(f"error: no *.yaml in {yaml_dir}", file=sys.stderr)
        return 2

    walker = Walker(schemas)
    walker.walk_all()
    rep = walker.finalize(str(yaml_dir))

    if args.format == "json":
        print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Input:     {yaml_dir}")
        print(f"Schemas:   {rep.schema_count}")
        print(f"Visited:   {rep.total_visited} leaf properties")
        print(f"With ex.:  {rep.with_example}")
        print(f"Missing:   {rep.missing_count}")
        print(f"Coverage:  {rep.coverage_pct}%")
        if rep.missing_fields:
            by_type: Counter[str] = Counter(m.type for m in rep.missing_fields)
            print(f"\nMissing by type:")
            for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"  {n:4d}  {t}")
            print(f"\nMissing paths (first {args.max_missing_print}):")
            for m in rep.missing_fields[: args.max_missing_print]:
                print(f"  {m.schema}: {m.path} [{m.type}]")
            remaining = len(rep.missing_fields) - args.max_missing_print
            if remaining > 0:
                print(f"  ... and {remaining} more")

    return 1 if args.strict and rep.missing_fields else 0


if __name__ == "__main__":
    sys.exit(main())
