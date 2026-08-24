# Current Work

Last updated: 2026-08-24

## Active objective

Complete the evidence-driven champion/challenger lifecycle on top of the immutable registry and deterministic evaluation gates.

## Active issue

#5 — `[IN PROGRESS][P1] Implement champion/challenger registry and promotion policy`

## Active branch

`agent/issue-5-champion-lifecycle`

## Active pull request

Not opened yet.

## Current status

- Issue #4 local CLI is complete and merged to `develop` through PR #15; repository `Check` passed
- `mlai` now provides network-free registration, evaluation, comparison, report, versioned JSON output, and CI policy exit codes
- Issue #5 lifecycle core added on the active branch
- versioned immutable promotion policies compose existing deterministic `MetricGate` rules
- immutable `PromotionDecision` records remain the authoritative lifecycle history
- replaceable champion aliases reference the exact accepted decision and evaluation run
- missing incumbent evidence produces `REVIEW`, not promotion
- rejected/reviewed challengers do not move the champion alias
- rollback requires a previously accepted target and appends a new accepted decision rather than rewriting history
- tests cover accept, protected-slice reject, human review, missing evidence, rollback, immutable policies, and candidate/evaluation mismatch

## Next action

Open the Issue #5 PR to `develop`, run repository `Check`, repair any failures, and merge autonomously only if all acceptance criteria pass and no human gate emerges. If merged, close #5 and advance the next dependency-eligible issue.

## Human decisions required

None for the current local lifecycle implementation unless review reveals a backward-incompatible consumer impact or another explicit human gate.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
