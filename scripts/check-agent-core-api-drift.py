#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# --- How to run ---
# Run from the repository root:
#   python3 scripts/check-agent-core-api-drift.py
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[1]
AGENT_DIR: Final = ROOT / ".agent" / "core-api"
YAML_FILES: Final = (
    AGENT_DIR / "rules.yaml",
    AGENT_DIR / "checks.yaml",
    AGENT_DIR / "examples.yaml",
    AGENT_DIR / "tools.yaml",
)
ADAPTERS: Final = (ROOT / "AGENTS.md", ROOT / "CLAUDE.md")
FORBIDDEN_ADAPTER_TERMS: Final = (
    "buf.validate",
    "FieldMask",
    "kubebuilder",
    "chat_message.proto",
    "make generate",
    "make lint",
)
FORBIDDEN_TRACKED_SURFACES: Final = (
    ROOT / ".claude" / "CLAUDE.md",
    ROOT / ".claude" / "rules",
)
SYMBOL_PATTERN_TEMPLATE: Final = r"\b(?:message|enum)\s+{symbol}\b"


@dataclass(frozen=True)
class ExampleReference:
    file_path: Path
    symbols: tuple[str, ...]


def main() -> int:
    violations = collect_violations()
    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("check-agent-core-api-drift: ok")
    return 0


def collect_violations() -> list[str]:
    violations: list[str] = []
    violations.extend(check_required_files())
    violations.extend(check_examples())
    violations.extend(check_adapters())
    violations.extend(check_forbidden_surfaces())
    return violations


def check_required_files() -> list[str]:
    violations: list[str] = []
    for path in YAML_FILES:
        if not path.is_file():
            violations.append(format_violation(path, "required agent package file is missing"))
    return violations


def check_examples() -> list[str]:
    examples_path = AGENT_DIR / "examples.yaml"
    if not examples_path.is_file():
        return [format_violation(examples_path, "required agent package file is missing")]

    references = parse_example_references(examples_path)
    violations: list[str] = []
    for reference in references:
        proto_path = ROOT / reference.file_path
        if not proto_path.is_file():
            violations.append(format_violation(reference.file_path, "referenced proto file does not exist"))
            continue

        content = proto_path.read_text(encoding="utf-8")
        for symbol in reference.symbols:
            if not proto_declares_symbol(content, symbol):
                message = f"referenced symbol {symbol} is not declared as a message or enum"
                violations.append(format_violation(reference.file_path, message))
    return violations


def parse_example_references(path: Path) -> list[ExampleReference]:
    references: list[ExampleReference] = []
    current_file: Path | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        file_match = re.match(r"\s*-\s+file:\s+(.+?)\s*$", line)
        if file_match:
            current_file = Path(file_match.group(1))
            continue

        symbols_match = re.match(r"\s*symbols:\s+\[(.*)]\s*$", line)
        if symbols_match and current_file is not None:
            symbols = parse_inline_symbols(symbols_match.group(1))
            references.append(ExampleReference(file_path=current_file, symbols=symbols))
            current_file = None

    return references


def parse_inline_symbols(raw_symbols: str) -> tuple[str, ...]:
    symbols: list[str] = []
    for raw_symbol in raw_symbols.split(","):
        symbol = raw_symbol.strip().strip("'\"")
        if symbol:
            symbols.append(symbol)
    return tuple(symbols)


def proto_declares_symbol(content: str, symbol: str) -> bool:
    pattern = SYMBOL_PATTERN_TEMPLATE.format(symbol=re.escape(symbol))
    return re.search(pattern, content) is not None


def check_adapters() -> list[str]:
    violations: list[str] = []
    for path in ADAPTERS:
        if not path.is_file():
            violations.append(format_violation(path, "adapter file is missing"))
            continue

        content = path.read_text(encoding="utf-8")
        if ".agent/core-api/README.md" not in content:
            violations.append(format_violation(path, "must mention .agent/core-api/README.md"))

        for term in FORBIDDEN_ADAPTER_TERMS:
            if term in content:
                message = f"must not copy Core API rule term {term}"
                violations.append(format_violation(path, message))
    return violations


def check_forbidden_surfaces() -> list[str]:
    violations: list[str] = []
    for path in FORBIDDEN_TRACKED_SURFACES:
        if path.exists():
            violations.append(format_violation(path, "stale Claude-specific rule surface must not exist"))

    openapi_ai = ROOT / (".openapi" + "-ai")
    if openapi_ai.exists():
        violations.append(format_violation(openapi_ai, "stale OpenAPI-only agent package must not exist"))
    return violations


def format_violation(path: Path, message: str) -> str:
    display_path = path.relative_to(ROOT) if path.is_absolute() else path
    return f"{display_path}: {message}"


if __name__ == "__main__":
    sys.exit(main())
