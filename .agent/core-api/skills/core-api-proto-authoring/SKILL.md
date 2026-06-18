---
name: core-api-proto-authoring
description: Use when creating or modifying Core API proto contracts in ch-proto-public, including service request/result messages, model/common public schemas, validation, comments, generated output expectations, and proto pattern discovery.
---

# Core API Proto Authoring

This skill is a harness. It is not the source of truth.

Read these files before changing Core API proto contracts:

1. `../../README.md`
2. `../../rules.yaml`
3. `../../examples.yaml`
4. `../../change-checklist.md`
5. `../../checks.yaml`
6. `../../tools.yaml`

Workflow:

- Stay inside `ch-proto-public`.
- Do not work on orchestrator or sibling repositories.
- Before editing, find the closest existing proto operation or schema pattern.
- Follow field numbering, validation, import, comment, and generation rules from `rules.yaml`.
- Use `examples.yaml` references to inspect live canonical proto implementations.
- Run matching checks from `checks.yaml`.
- Report skipped checks with reasons.

Do not:

- Invent new service structure from scratch when a nearby pattern exists.
- Hand-edit generated Go or Java files.
- Modify `shared/v1/validation/`.
- Copy separate rules into tool-specific files.
