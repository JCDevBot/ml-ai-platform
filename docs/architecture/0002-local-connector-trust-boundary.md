# Local connector trust boundary

Date: 2026-08-25
Status: accepted for local prototype

## Context

Issue #7 requires a connector that lets local or self-hosted environments participate in the ML/AI lifecycle without inbound network access or unrestricted filesystem ingestion. The repository owner approved a bounded local-only prototype: outbound-only connections, explicit data-movement modes, allow-listed scopes, conservative secret/private exclusions, independently revocable connector identities, fake transports in tests, and no production credentials or real sensitive-data transfer.

## Decision

The connector boundary has four explicit pieces.

### Connector identity

A connector identity contains a stable connector ID, workspace ID, explicit movement permissions, creation time, and optional revocation time. It contains no credential material. Revocation is local policy state and immediately prevents new submissions.

A future production transport may associate real authentication material with this identity only after a separate security/privacy review.

### Data-movement mode

Every submission declares exactly one mode:

1. `metadata-only` — the connector may send bounded metadata such as path identity, byte size, and content hash; file bytes remain local.
2. `upload` — the connector may send bytes only for files explicitly named by the job and admitted by the path policy.
3. `local-execution` — work executes in the local environment and the connector sends bounded result data plus metadata; source file bytes are not included in the outbound envelope.

Permissions are mode-specific (`movement:<mode>`), so enabling metadata-only does not imply upload permission.

### Filesystem scope

Filesystem access is deny-by-default outside configured roots. Paths are individually resolved and checked against allow-listed roots. Directory submission is rejected rather than recursively traversed. Common credential/private path names such as `.env`, `.ssh`, `.aws`, key files, `credentials`, `secrets`, and `private` are excluded by default even when they live under an otherwise allowed root.

This prototype deliberately supports explicit files rather than directory ingestion.

### Transport direction

The platform defines only an outbound `send(envelope)` transport protocol. There is no inbound listener or callback contract in the connector core. The provided transport is an in-memory fake for deterministic tests and local prototypes.

## Local-execution result boundary

Local-execution results may include metrics, findings, run IDs, summaries, and artifact references. Common raw-row containers (`rows`, `records`, `raw_rows`, `examples`, `samples`) are rejected by the prototype before the outbound transport is invoked.

This is a conservative first boundary rather than a claim that field-name filtering alone is a complete data-loss-prevention system. Expanding what may leave a local environment requires explicit policy work and, where sensitive data is involved, a new human gate.

## Consequences

- hosted infrastructure never needs inbound access to local/private networks;
- metadata-only and local-execution can keep raw records local;
- upload capability is separately permissioned and file-scoped;
- a connector cannot recursively ingest an allowed directory by default;
- revocation is independent per connector identity;
- tests require no credentials, provider SDKs, network service, or sensitive data.

## Deferred work / human gate

This decision does not authorize:

- production credentials or token storage;
- a concrete authenticated network protocol;
- hosted deployment or subscriptions;
- real sensitive-data transfer;
- broader filesystem discovery/recursive ingestion;
- changes to privacy guarantees.

Those require security/privacy review and explicit human approval before implementation or production use.
