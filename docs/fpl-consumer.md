# FPL consumer validation

Issue #6 validates the platform against a focused Fantasy Premier League forecasting consumer without adding FPL behavior to the core package.

## Historical fixture

The integration uses a deliberately small, pinned slice of the public `vaastav/Fantasy-Premier-League` 2025-26 dataset. The fixture records the exact repository paths and Git blob SHAs used for gameweeks 36, 37, and 38, so tests remain deterministic even if upstream data later changes.

The focused sample contains 13 players and the fields needed for this proof: position, element ID, FPL points, ICT index, and minutes.

## Temporal boundary

The consumer treats gameweeks 36-37 as information available before gameweek 38:

- training cutoff: 2026-05-20T00:00:00Z;
- learned model training pair: GW36 features -> GW37 points;
- prediction features: GW37 only;
- target labels: resolved GW38 points;
- resolved evaluation snapshot: 2026-05-25T00:00:00Z.

GW38 labels never participate in model fitting or prediction feature construction. The consumer registers separate training-cutoff and resolved-evaluation `DatasetRef` records, with the resolved snapshot referencing the training snapshot as its parent.

## Candidate types

Two materially different candidates are registered through the platform:

1. `heuristic:last-gameweek-points` — predicts GW38 points directly from GW37 points.
2. `linear:ridge` — a small consumer-side ridge regression model trained on GW36 features and GW37 labels, then applied to GW37 features to forecast GW38.

The ridge implementation is intentionally standard-library-only and lives under `examples/fpl_consumer/`; it is consumer feature/model logic, not platform core behavior.

## Platform-owned evaluation

Both candidates are evaluated through the reusable platform APIs. Each immutable evaluation run contains:

- overall MAE and RMSE;
- position-sliced regression metrics for DEF/FWD/MID;
- probability metrics for the event `GW38 points >= 2` (Brier score, log loss, calibration error);
- exact dataset, candidate, experiment, code, and config lineage.

Comparison findings are produced by `comparison_findings`, not FPL-specific code, and are persisted as platform `Finding` records.

## Promotion result

On this historical sample, the heuristic baseline has MAE `2/13` (~0.154), while the ridge challenger has MAE ~0.424. This is intentionally not hidden or tuned away: the lifecycle layer accepts the baseline as the initial champion and rejects the ridge challenger under a no-regression MAE policy. The champion alias remains on the baseline while both decisions remain in immutable history.

This demonstrates that a consumer can use the platform to reject an inferior learned model rather than privileging model complexity.

## Abstraction assessment

The existing platform abstractions were sufficient for this proof:

- `DatasetRef` handles training/resolved temporal snapshots and parent lineage;
- `CandidateRef` handles heterogeneous candidate adapters;
- `ExperimentSpec` and `EvaluationRun` capture reproducible evaluation lineage;
- reusable regression/probability/slice evaluators handle FPL outcomes without domain branching;
- `Finding` captures comparison evidence;
- `ChampionLifecycle` and `PromotionPolicy` manage champion/challenger decisions.

No core contract change was required.

A future production FPL consumer will likely add richer consumer-side adapters for official FPL ingestion, historical feature stores, human forecast records, and scheduled gameweek resolution. Those remain consumer responsibilities unless repeated use across unrelated domains demonstrates a genuinely reusable platform abstraction.
