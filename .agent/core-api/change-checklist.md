# Core API Proto Change Checklist

Use this checklist before and after changing Core API proto contracts.

## Before Editing

- [ ] Confirm the change belongs in `ch-proto-public`.
- [ ] Confirm no orchestrator or sibling repository work is required in this branch.
- [ ] Run `git status --short` and account for existing local changes.
- [ ] Find the closest existing operation or model pattern with `rg`.
- [ ] Read the surrounding proto file before editing.
- [ ] Decide whether the operation is an independent resource or dependent operation.

## During Editing

- [ ] Follow package and language option rules from `rules.yaml`.
- [ ] Use fully qualified references for cross-package messages.
- [ ] Import only used proto files.
- [ ] Preserve existing field numbers.
- [ ] Add new fields at the next safe number.
- [ ] Use `buf.validate` for required fields and constraints.
- [ ] Keep kubebuilder markers synchronized with `buf.validate`.
- [ ] Keep public comments observable to API consumers.
- [ ] Avoid internal storage, table, and private service details in comments.

## Pattern Evolution

- [ ] If this change creates or changes a reusable proto pattern, update `.agent/core-api/rules.yaml`.
- [ ] If the canonical example changes, update `.agent/core-api/examples.yaml`.
- [ ] If enforcement changes, update `.agent/core-api/checks.yaml` and `scripts/check-agent-core-api-drift.py`.
- [ ] Mention the pattern migration in the final handoff or PR description.

## After Editing

- [ ] If proto files changed, run `make generate`.
- [ ] Run `buf format --diff --exit-code`.
- [ ] Run `make lint`.
- [ ] Run `buf breaking --against '.git#branch=main'` for breaking-sensitive PR work.
- [ ] Run `python3 scripts/check-agent-core-api-drift.py` when `.agent/core-api`, adapters, or referenced proto patterns changed.
- [ ] Report any skipped checks with reasons.
