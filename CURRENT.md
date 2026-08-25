# Current Work

Last updated: 2026-08-25

## Active objective

Hold the completed local-first roadmap state on `develop` and await the next explicit human-gated product direction.

## Active issue

None. All currently defined implementation issues are complete.

## Active branch

`develop`

## Active pull request

None after the final handoff-state update merges.

## Current status

- Issues #2–#8, #21, and #23 are complete and merged to `develop`; repository checks passed
- core contracts, immutable local registry, deterministic evaluation/findings, local CLI, champion/challenger lifecycle, FPL consumer proof, provider-neutral LLM/RAG/agent evaluation, bounded local connector prototype, deterministic experiment recommendations, and read-only external forecast adapter proof are implemented
- connector work remains local/outbound-only with explicit movement modes, allow-listed files, revocable identities, fake transport, and no production credentials
- experiment recommendations reference exact evidence and remain subordinate to lifecycle/promotion policy
- external forecast adapters normalize timestamped source/target probability evidence and explicitly exclude trading or financial execution
- `main` still contains the earlier bootstrap release; the completed capability set is on `develop`

## Next action

Human decision required before further consequential work. The two meaningful next directions are:

1. approve `develop` -> `main` promotion to publish the completed local-first platform capability set; and/or
2. explicitly approve a bounded hosted control-plane design scope if work should proceed toward organizations/workspaces, authentication, subscriptions, schedules, dashboards, and shared audit history.

## Human decisions required

At least one of the following:

- explicit approval to promote `develop` to `main`; or
- a bounded approval for hosted control-plane/authentication/privacy/billing architecture before that trust boundary is designed or implemented.

A separate human gate remains required before production credentials, hosted deployment, billing, real sensitive-data transfer, production auto-promotion outside existing policy controls, or any trading/financial execution capability.

## Do not begin

- `develop` to `main` promotion without explicit human approval
- hosted authentication/credential trust-boundary design without explicit approval
- production deployment or hosted billing
- real credentials or secrets
- real sensitive-data transfer
- unrestricted filesystem ingestion
- production auto-promotion outside existing policy controls
- trading, wallets, orders, deposits, or financial execution
