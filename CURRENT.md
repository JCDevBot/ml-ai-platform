# Current Work

Last updated: 2026-08-24

## Active objective

Complete the local CLI and CI-friendly developer workflow on top of the core registry and evaluation engine.

## Active issue

#4 — `[IN PROGRESS][P1] Add local CLI and CI-friendly evaluation workflow`

## Active branch

`agent/issue-4-local-cli`

## Active pull request

Not opened yet.

## Current status

- repository bootstrap is on `main`; ordinary implementation continues through `develop`
- Issues #2 and #3 are complete on `develop`
- local CLI command surface added for dataset/candidate registration, evaluation, comparison, and reports
- YAML/JSON local documents feed the existing contracts and evaluation engine; the CLI does not execute model artifacts
- JSON output uses versioned envelope `mlai.cli.v1`
- deterministic policy rejection has a dedicated non-zero exit code for CI
- end-to-end tests cover registration, evaluation, protected-slice rejection, reporting, invalid input, and idempotent registration
- CLI documentation and README entry point added

## Next action

Open the Issue #4 PR to `develop`, inspect repository `Check`, repair any deterministic failure, and merge autonomously only if all acceptance criteria pass and no human gate emerges. Then advance Issue #5 to READY.

## Human decisions required

None for the current ordinary implementation route unless CI/review reveals a backward-incompatible contract concern or another explicit human gate.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
