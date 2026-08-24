# Current Work

Last updated: 2026-08-24

## Active objective

Build the deterministic evaluation engine and evidence-based findings layer.

## Active issue

#3 — `[IN PROGRESS][P1] Build evaluation engine and deterministic findings`

## Active branch

`agent/issue-3-evaluation-engine`

## Active pull request

Not opened yet.

## Current status

- repository bootstrap is on `main`; ordinary implementation continues through `develop`
- Issue #2 core contracts/local registry is complete and merged to `develop`
- Issue #3 activated and assigned
- deterministic regression metrics implemented: MAE and RMSE
- deterministic binary classification metrics implemented: precision, recall, F1, and confusion-matrix cells
- probability metrics implemented: Brier score, log loss, and calibration error with bin summary
- reusable slice evaluation implemented
- baseline/challenger comparison findings implemented
- deterministic threshold, calibration, and protected-slice regression gates implemented
- synthetic test demonstrates overall challenger improvement rejected by protected-slice regression
- known-answer and invalid-input tests added

## Next action

Open the Issue #3 PR to `develop`, inspect repository CI, repair any failures, then verify all acceptance criteria before autonomous merge if policy permits.

## Human decisions required

None for this ordinary implementation route unless a backward-incompatible public-contract change or another explicit human gate emerges.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
