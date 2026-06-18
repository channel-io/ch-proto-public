# Core API Proto Authoring

This directory is the canonical source of truth for writing and changing Core API proto contracts in `ch-proto-public`.

## Scope

- Owns `coreapi/service/*.proto`, `coreapi/model/*.proto`, and `coreapi/common/*.proto` authoring guidance.
- Owns guidance for generated output expectations under `coreapi/go/` and `coreapi/java/`.
- Owns guidance for repo-local checks that protect Core API proto contracts.

## Out Of Scope

- Orchestrator work.
- Sibling repository implementation work.
- Manual edits to generated files.
- Vendored files under `shared/v1/validation/`.

## Required Reading Order

1. `rules.yaml`
2. `examples.yaml`
3. `change-checklist.md`
4. `checks.yaml`
5. `tools.yaml`
6. `skills/core-api-proto-authoring/SKILL.md` when an agent supports skills

## Core Principle

Do not invent Core API proto structure from scratch. Before editing, find the closest existing proto operation or model pattern and follow it unless the change intentionally evolves that pattern.

## Drift Policy

The canonical examples are the referenced proto implementations in `coreapi/`. `examples.yaml` indexes those examples; it must not become a stale copied version of them.

When a change introduces a better recurring pattern, update the representative proto implementation, this package's rules/checks/examples as needed, and `scripts/check-agent-core-api-drift.py` if enforcement changes.
