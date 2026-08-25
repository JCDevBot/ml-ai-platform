# ML / AI Platform Agent Steering

## Repository authority

GitHub state and checked-in files are authoritative. This repository consumes shared engineering mechanics from the pinned Engineering Platform release recorded in `engineering-platform.yaml`, while ML/AI product truth and architecture remain local.

Instruction precedence:

1. safety, security, platform, and tool constraints;
2. direct human instructions for the active task;
3. accepted GitHub issue outcome, scope, and acceptance criteria;
4. repository-local product and architecture documents;
5. repository-local agent steering and explicit exceptions;
6. synchronized/pinned Engineering Platform steering;
7. general engineering conventions.

## Required startup reads

At the beginning of every run:

1. verify access to `JonCunninghamDev/ml-ai-platform` with a real GitHub call;
2. confirm `main` is the default branch;
3. read `README.md`;
4. read `engineering-platform.yaml` and use only the pinned published platform release as shared steering;
5. read this file, `ROADMAP.md`, and `CURRENT.md`;
6. read the active issue and relevant files under `docs/architecture/`;
7. inspect open pull requests, CI, reviews, comments, and unresolved threads;
8. verify partially completed writes before repeating them;
9. continue the lowest-numbered `IN PROGRESS` issue, otherwise the highest-priority eligible `READY` issue.

Do not rely on conversational memory when repository state can answer the question.

## Product objective

Build a domain-agnostic ML/AI lifecycle platform that can register versioned datasets and candidate systems, run reproducible evaluations, generate deterministic findings and recommendations, manage champion/challenger lifecycle decisions, and support classical ML, forecasting, LLM, RAG, and agentic systems through adapters rather than product-specific branching.

FPL forecasting is an initial consumer and proving ground, not a core domain dependency.

## Core architectural boundaries

The platform should keep these responsibilities separate:

- dataset identity, lineage, and snapshots;
- candidate/model adapters;
- experiment specifications;
- evaluators and metrics;
- deterministic findings and diagnostics;
- optional LLM-generated explanation/suggestions built on measured results;
- registry and promotion decisions;
- CLI/API/control-plane interfaces;
- local or self-hosted connectors;
- consumer-specific feature engineering and domain resolution logic.

The platform must not make an LLM the authoritative source for deterministic metric calculation, comparison, or policy-gated promotion decisions.

## Development and tooling

- Python is the initial implementation language.
- Use `mise` as the project task/tool entry point.
- Use `uv` for Python dependency and environment management.
- Prefer small, explicit interfaces over framework-heavy abstractions.
- Keep adapters optional so the core package does not require every supported ML/LLM provider.
- Automated tests must not require paid external APIs or secrets.
- Use deterministic fixtures and seeded randomness for CI.

## Work management and delivery

- GitHub Issues are the backlog and scope authority.
- Ordinary branches use `agent/issue-<number>-<slug>` from `develop`.
- Ordinary pull requests target `develop`.
- `develop` to `main` is a release/promotion route and requires explicit human approval.
- Use one issue per PR unless the issue explicitly defines grouped work.
- Maintain at most two active implementation branches.
- Record follow-up work as issues instead of silently expanding scope.

## Autonomous implementation authority

The repository owner explicitly authorizes autonomous engineering work with minimal intervention.

The default decision rule is:

> If a decision is reversible, local to the accepted issue, testable, and does not cross a human gate, choose a reasonable option, document it when durable, validate it, and continue.

The agent may autonomously:

- choose ordinary implementation details and libraries consistent with repository standards;
- add tests, documentation, diagnostics, and safe refactors required by the issue;
- create ADRs for meaningful but reversible technical choices;
- create follow-up issues;
- diagnose and repair CI failures;
- retry transient failures up to two times;
- make bounded compatibility-preserving schema/interface additions;
- reject an implementation approach and try another when evidence shows it is inferior;
- continue recurring/hourly work from repository state without requesting permission to resume.

Low-risk PRs into `develop` may merge autonomously only when all required checks pass, acceptance criteria are satisfied, no unresolved review/thread remains, and none of the human gates below apply.

## Human gates

Stop at a precise human decision before:

- changing shared Engineering Platform authority or pretending unreleased shared steering is published;
- merging backward-incompatible public contracts with consumer impact;
- adding or changing credentials, secrets, authentication trust boundaries, or sensitive-data handling;
- destructive or difficult-to-reverse data migrations;
- enabling production writes, deployment, billing, or material cloud/LLM spend;
- expanding data collection beyond configured/consented sources;
- changing privacy guarantees or exporting data that was previously local-only;
- promoting `develop` to `main`;
- making a consequential cross-repository change whose blast radius cannot be bounded and tested locally.

A blocker must state the exact decision, permission, credential, setting, or dependency required and the smallest human action that resolves it.

## Recurring / interrupted runs

Each recurring invocation is a fresh process. Recover from GitHub state:

1. inspect the active issue and PR;
2. inspect latest commits and CI;
3. verify whether the prior run's intended write already landed;
4. repair failures before starting unrelated work;
5. make the largest safe, reviewable increment available;
6. update durable state (`CURRENT.md`, issue, or PR) before stopping;
7. leave no essential next-step information only in chat.

Waiting on CI is not a blocker; inspect independent non-overlapping work only when doing so does not create conflicting branches or dilute the active issue.

## Validation and definition of done

Before a PR is ready for review or autonomous merge:

- run the standard project check;
- run relevant unit/integration tests;
- validate schemas and serialized examples when contracts change;
- verify tests are deterministic and do not rely on live paid services;
- document compatibility impact and rollback;
- verify issue acceptance criteria explicitly;
- update architecture/README/roadmap when durable behavior changes.

An issue is complete only when its intended branch contains the accepted change and dependent issue state has been updated.
