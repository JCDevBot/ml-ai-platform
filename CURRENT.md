# Current Work

Last updated: 2026-08-24

## Active objective

Promote the completed repository bootstrap to `main`, then begin the core contract/local-registry implementation.

## Active issue

#1 — `[REVIEW][P0] Bootstrap ML/AI platform foundation`

## Active branch

`develop`

## Active pull request

Bootstrap implementation PR #9 merged to `develop` at `61685bb24aa98ad2489a8412b61043f956108df9`.

## Current status

- repository initialized with `main` and `develop`
- published Engineering Platform `v0.1.0` pinned in `engineering-platform.yaml`
- repository-local agent steering defines autonomous reversible/testable work and explicit human gates
- initial roadmap defines local-first ML/AI lifecycle phases
- architecture decision 0001 defines dataset, candidate, evaluation, findings, registry/promotion, and connector boundaries
- Python 3.12 package, mise/uv tasks, smoke test, and GitHub Actions check workflow added
- dependency-ordered implementation backlog created as issues #2–#8
- bootstrap PR #9 passed CI and merged to `develop`
- Issue #2 is READY for core contracts/local registry work

## Next action

Prepare `develop` → `main` bootstrap promotion for explicit human approval. Independent implementation work may continue from `develop`; when starting the next ordinary task, move Issue #2 to IN PROGRESS and branch from current `develop`.

## Human decisions required

Explicit approval is required before merging the bootstrap promotion from `develop` to `main`.

## Do not begin

- production deployment or hosted billing
- credentials or secrets
- paid model-provider integration
- broad filesystem connector ingestion
- FPL-specific implementation inside core modules
- `develop` to `main` promotion without explicit human approval
