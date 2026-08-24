# Current Work

Last updated: 2026-08-24

## Active objective

Bootstrap a reproducible, agent-operable foundation for the ML/AI Platform.

## Active issue

#1 — `[IN PROGRESS][P0] Bootstrap ML/AI platform foundation`

## Active branch

`agent/issue-1-bootstrap-platform`

## Active pull request

Not opened yet.

## Current status

- repository initialized with `main` and `develop`
- published Engineering Platform `v0.1.0` pinned in `engineering-platform.yaml`
- repository-local agent steering defines autonomous reversible/testable work and explicit human gates
- initial roadmap defines local-first ML/AI lifecycle phases
- architecture decision 0001 defines dataset, candidate, evaluation, findings, registry/promotion, and connector boundaries
- Python tooling and CI bootstrap are the next implementation step

## Next action

Complete Python/mise/uv tooling, deterministic CI, and initial smoke tests; then create the first implementation backlog and open a draft PR to `develop`.

## Human decisions required

None for the current bootstrap increment.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
