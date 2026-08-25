# Current Work

Last updated: 2026-08-25

## Active objective

Prove provider-neutral read-only external forecast normalization and comparison without introducing financial execution.

## Active issue

#23 — `[IN PROGRESS][P3] Add read-only external forecast adapter contracts`

## Active branch

`agent/issue-23-forecast-adapters`

## Active pull request

Not opened yet.

## Current status

- Issues #2–#8 and #21 are complete and merged to `develop`; repository checks passed
- Issue #7 added the approved outbound-only local connector prototype with explicit movement modes, allow-listed files, revocable identities, local fake transport, and no production credentials
- Issue #21 added deterministic evidence-linked experiment recommendations and bounded search proposals while leaving promotion policy authoritative
- Issue #23 branch defines provider-neutral forecast observations with source/target identity, probability, timestamp, read-only adapter protocol, and explicit resolution lineage
- forecast evaluation reuses the existing deterministic probability evaluator and rejects post-resolution observations
- tests compare a fake external consensus against an internal baseline with known-answer metrics and require no provider, network service, credential, trading, wallet, order, or payment surface

## Next action

Open the Issue #23 PR to `develop`, run repository `Check`, repair any failure, and merge autonomously if all acceptance criteria remain satisfied and no human gate is crossed.

## Human decisions required

None for Issue #23's read-only, local-fixture scope.

A human gate is still required before:

- `develop` to `main` promotion;
- production credentials/authentication changes;
- hosted deployment or billing;
- real sensitive-data transfer;
- production auto-promotion outside existing policy controls;
- any trading, wallet, order, or financial execution capability.

## Do not begin

- trading, wallets, orders, deposits, or financial execution
- production deployment or hosted billing
- real credentials or secrets
- real sensitive-data transfer
- unrestricted filesystem ingestion
- provider-backed paid model calls in tests
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
