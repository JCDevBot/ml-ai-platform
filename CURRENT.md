# Current Work

Last updated: 2026-08-24

## Active objective

Begin the local CLI and CI-friendly developer workflow on top of the completed core registry and evaluation engine.

## Active issue

#4 — `[READY][P1] Add local CLI and CI-friendly evaluation workflow`

## Active branch

`develop`

## Active pull request

None.

## Current status

- repository bootstrap is on `main`; ordinary implementation continues through `develop`
- Issue #2 core contracts/local registry is complete and merged to `develop`
- Issue #3 evaluation engine/deterministic findings is complete and merged to `develop` through PR #13
- regression, binary classification, probability/calibration, slice evaluation, baseline/challenger findings, and deterministic gating are available in the core
- repository `Check` passed for PR #13
- Issue #4 is unblocked and READY

## Next action

Activate Issue #4, branch `agent/issue-4-local-cli` from current `develop`, and implement the smallest complete local CLI workflow using the existing contracts, registry, and evaluation engine. Preserve stable machine-readable output for CI and keep the default workflow network-free.

## Human decisions required

None for the next ordinary implementation route unless a backward-incompatible public-contract change or another explicit human gate emerges.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
