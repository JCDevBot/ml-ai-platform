# Current Work

Last updated: 2026-08-24

## Active objective

Complete provider-neutral LLM, RAG, and agent evaluation while keeping deterministic evidence distinct from optional judge-model evidence.

## Active issue

#8 — `[IN PROGRESS][P2] Add LLM, RAG, and agent evaluation adapters`

## Active branch

`agent/issue-8-generative-evaluation`

## Active pull request

Not opened yet.

## Current status

- Issues #4, #5, and #6 are complete and merged to `develop` through PRs #15, #16, and #17; all repository checks passed
- FPL consumer proof uses pinned historical data and required no core contract changes
- Issue #7 connector/data-movement work remains blocked by explicit repository human gates around authentication trust boundaries, privacy, and sensitive-data handling
- provider-neutral `GenerativeCase`, `GenerativeOutput`, and `GenerativeCandidate` adapter protocol added without provider SDK dependencies
- deterministic generative metrics include task accuracy, structured-output validity, tool-selection accuracy, retrieval precision/recall, unsupported-claim rate, latency, and cost
- optional `JudgeResult` aggregation requires judge identity/config/scale provenance and emits `evidence_type=judge_model` plus `authoritative_ground_truth=false`
- provider-free fake candidate tests cover deterministic metrics, judge provenance, judge-mixing rejection, and case/output alignment
- incident-triage fixture compares an LLM-prompt baseline with a tool-agent challenger using reusable registry, findings, and champion/challenger lifecycle components
- incident challenger improves deterministic accuracy/structure/tool/claim metrics, exposes a separate cost regression finding, and is promoted under deterministic gates that do not rely on judge score

## Next action

Open the Issue #8 PR to `develop`, run repository `Check`, repair any failures, and merge autonomously only if all acceptance criteria pass and no human gate emerges. If merged, close #8 and leave Issue #7 blocked with the exact human trust-boundary decision required.

## Human decisions required

Issue #7 requires explicit approval before designing or implementing connector authentication trust boundaries and sensitive-data movement policy. Smallest resolving action: approve proceeding with a local-only connector trust/data-movement design under the stated metadata-only/upload/local-execution principles, without production credentials or deployment.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- provider-backed paid model calls in tests
- connector authentication/data-movement implementation without the Issue #7 human gate
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
