# Current Work

Last updated: 2026-08-24

## Active objective

Complete the first external-consumer proof using leakage-safe historical Fantasy Premier League forecasting data without adding FPL behavior to the core package.

## Active issue

#6 — `[IN PROGRESS][P1] Integrate FPL forecasting as the first external consumer`

## Active branch

`agent/issue-6-fpl-consumer`

## Active pull request

Not opened yet.

## Current status

- Issues #4 and #5 are complete and merged to `develop` through PRs #15 and #16; both repository checks passed
- focused FPL consumer lives under `examples/fpl_consumer/`, outside `src/ml_ai_platform`
- historical fixture pins exact 2025-26 GW36/GW37/GW38 source paths and Git blob SHAs from `vaastav/Fantasy-Premier-League`
- separate training-cutoff and resolved-evaluation dataset records preserve temporal lineage
- baseline candidate uses last-gameweek points; learned candidate is a consumer-side ridge model trained GW36 -> GW37 and applied to GW37 to predict GW38
- GW38 labels are used only for evaluation after the prediction cutoff
- reusable platform regression, position-slice, probability/calibration, comparison finding, registry, and champion/challenger lifecycle components are used unchanged
- on the pinned sample, the baseline MAE is 2/13 (~0.154) and the ridge MAE is ~0.424; the deterministic no-regression policy rejects the learned challenger and retains the baseline champion
- tests assert temporal boundaries, exact source SHAs, two candidate adapter types, regression/probability metrics, reusable findings/promotion decisions, and absence of FPL logic in the core package
- integration assessment documents that no core contract change was required

## Next action

Open the Issue #6 PR to `develop`, run repository `Check`, repair any deterministic failures, and merge autonomously only if all acceptance criteria pass and no human gate emerges. If merged, close #6 and determine the next dependency-eligible issue without crossing connector/privacy or cross-repository gates.

## Human decisions required

None for this focused in-repository consumer proof. A future change to the separate FPL application remains a separate cross-repository decision if its blast radius cannot be bounded locally.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
