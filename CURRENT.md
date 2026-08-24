# Current Work

Last updated: 2026-08-24

## Active objective

Await explicit human approval for the connector authentication/privacy trust-boundary design before beginning the final currently defined backlog item.

## Active issue

#7 — `[BLOCKED][P2] Build outbound local connector and data-movement policies`

## Active branch

`develop`

## Active pull request

None after the blocker-handoff update is merged.

## Current status

- Issues #4, #5, #6, and #8 are complete and merged to `develop` through PRs #15, #16, #17, and #18; all repository checks passed
- local CLI provides network-free registration, evaluation, comparison, reports, versioned JSON output, and CI policy exit codes
- champion/challenger lifecycle has immutable versioned policy/decision evidence, review/reject gates, aliases, and rollback history
- FPL is validated as the first external consumer using pinned leakage-safe historical data with no FPL branching in core
- provider-neutral LLM/RAG/agent evaluation is implemented with deterministic task/structure/tool/retrieval/claim/latency/cost metrics
- judge-model evidence is explicitly non-authoritative and retains judge identity/configuration provenance
- provider-free incident-triage evaluation feeds the same immutable registry/findings/promotion lifecycle as classical ML
- Issue #7 is the only currently defined incomplete backlog item

## Exact blocker

Issue #7 requires designing connector identity, permissions/revocation, authenticated outbound transport, and policies governing metadata-only, upload, and local-execution data movement. `AGENTS.md` requires a human gate before adding or changing authentication trust boundaries, privacy guarantees, or sensitive-data handling. Those concerns are central to Issue #7 rather than incidental implementation details, so autonomous work must stop before designing the trust boundary.

## Smallest human action that resolves the blocker

Explicitly approve this bounded direction:

> Proceed with Issue #7's local-only connector trust/data-movement design and prototype using outbound-only connections, explicit metadata-only/upload/local-execution modes, allow-listed artifact/path scopes, secrets/private paths excluded by default, independently revocable connector identities, local fake transports in tests, and no production credentials, hosted deployment, billing, or real sensitive-data transfer.

After that approval, move Issue #7 to IN PROGRESS, branch `agent/issue-7-local-connector` from `develop`, and implement only within those approved boundaries.

## Human decisions required

The bounded Issue #7 approval above.

## Do not begin

- connector authentication/data-movement design or implementation until that approval is explicit
- production deployment or hosted billing
- real credentials or secrets
- real sensitive-data transfer
- provider-backed paid model calls in tests
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
