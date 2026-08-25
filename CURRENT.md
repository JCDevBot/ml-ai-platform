# Current Work

Last updated: 2026-08-25

## Active objective

Implement the approved local-only outbound connector trust/data-movement design and prototype.

## Active issue

#7 — `[IN PROGRESS][P2] Build outbound local connector and data-movement policies`

## Active branch

`agent/issue-7-local-connector`

## Active pull request

None yet.

## Current status

- Issues #4, #5, #6, and #8 are complete and merged to `develop`; all repository checks passed
- local CLI provides network-free registration, evaluation, comparison, reports, versioned JSON output, and CI policy exit codes
- champion/challenger lifecycle has immutable versioned policy/decision evidence, review/reject gates, aliases, and rollback history
- FPL is validated as the first external consumer using pinned leakage-safe historical data with no FPL branching in core
- provider-neutral LLM/RAG/agent evaluation is implemented with deterministic task/structure/tool/retrieval/claim/latency/cost metrics
- judge-model evidence is explicitly non-authoritative and retains judge identity/configuration provenance
- provider-free incident-triage evaluation feeds the same immutable registry/findings/promotion lifecycle as classical ML
- the repository owner explicitly approved the bounded Issue #7 connector trust/data-movement design on 2026-08-25

## Approved Issue #7 boundary

Proceed with a local-only connector trust/data-movement design and prototype using:

- outbound-only connections;
- explicit `metadata-only`, `upload`, and `local-execution` modes;
- allow-listed artifact/path scopes;
- secrets/private paths excluded by default;
- independently revocable connector identities;
- local fake transports in tests;
- no production credentials;
- no hosted deployment or billing;
- no real sensitive-data transfer.

This approval clears the repository human gate for designing and implementing Issue #7 only within those bounds.

## Next action

Continue Issue #7 from `agent/issue-7-local-connector`. Define connector identity, scope, revocation, movement-mode contracts, outbound transport abstraction, safe path policy, local fake transport, and deterministic tests. Open an ordinary PR to `develop` when a coherent increment is ready.

## Human decisions required

None for the approved local-only Issue #7 prototype. A new human gate is required before production credentials, hosted deployment, billing, real sensitive-data transfer, or expansion of the approved trust boundary.

## Do not begin

- production deployment or hosted billing
- real credentials or secrets
- real sensitive-data transfer
- unrestricted filesystem ingestion
- provider-backed paid model calls in tests
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
