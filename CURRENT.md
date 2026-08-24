# Current Work

Last updated: 2026-08-24

## Active objective

Implement the first domain-neutral ML/AI lifecycle contracts and immutable local registry.

## Active issue

#2 — `[IN PROGRESS][P1] Implement core ML/AI contracts and local registry`

## Active branch

`agent/issue-2-core-contracts-registry`

## Active pull request

Not opened yet.

## Current status

- bootstrap foundation promoted to `main` through PR #11 with explicit human approval
- Issue #1 closed as complete
- Issue #2 activated and assigned
- domain-neutral contract layer added for datasets, candidates, experiments, metrics, findings, evaluation runs, and promotion decisions
- deterministic canonical JSON and content identity helpers added
- filesystem-backed immutable registry added with exclusive-create semantics and path-safety validation
- initial contract and registry tests added

## Next action

Open the Issue #2 pull request to `develop`, inspect CI, repair any deterministic failures, then continue against the issue acceptance criteria.

## Human decisions required

None for the current ordinary implementation route into `develop` unless a backward-incompatible public-contract decision or another explicit human gate emerges.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
