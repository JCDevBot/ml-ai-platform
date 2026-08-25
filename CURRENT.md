# Current Work

Last updated: 2026-08-25

## Active objective

Implement deterministic, evidence-linked recommendations for the next bounded experiment.

## Active issue

#21 — `[IN PROGRESS][P2] Add deterministic autonomous experiment recommendations`

## Active branch

`agent/issue-21-experiment-recommendations`

## Active pull request

Not opened yet.

## Current status

- Issues #2–#8 are complete and merged to `develop`; all repository checks passed
- Issue #7 added the approved outbound-only local connector prototype with explicit movement modes, allow-listed files, revocable identities, local fake transport, and no production credentials
- local CLI, lifecycle/promotion policy, FPL consumer proof, and provider-neutral LLM/RAG/agent evaluation are complete
- Phase 8 roadmap work is now tracked by Issue #21
- current Issue #21 branch adds a domain-neutral recommendation contract, deterministic finding-to-recommendation rules, and bounded deterministic search-space enumeration
- tests cover regression, protected-slice, calibration, threshold, deterministic ordering, search bounds, and a rejected challenger producing a next-experiment recommendation

## Next action

Open the Issue #21 PR to `develop`, run repository `Check`, repair any failure, and merge autonomously if all acceptance criteria remain satisfied and no human gate is crossed.

## Human decisions required

None for Issue #21's local deterministic recommendation scope.

A human gate is still required before:

- `develop` to `main` promotion;
- production credentials/authentication changes;
- hosted deployment or billing;
- real sensitive-data transfer;
- production auto-promotion outside existing policy controls.

## Do not begin

- production deployment or hosted billing
- real credentials or secrets
- real sensitive-data transfer
- unrestricted filesystem ingestion
- provider-backed paid model calls in tests
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
