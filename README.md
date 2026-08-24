# ML / AI Platform

Domain-agnostic infrastructure for registering datasets and model candidates, running reproducible evaluations, producing deterministic findings, and managing model lifecycle decisions across classical ML, forecasting, LLM, RAG, and agentic systems.

The platform is intentionally **local-first**. The first milestone is a reusable evaluation/lifecycle core that works from a developer repository without a hosted control plane. Hosted subscriptions, connectors, and team services come later.

## Core responsibilities

The platform owns reusable mechanics for:

- versioned dataset identity and lineage;
- heterogeneous candidate/model adapters;
- experiment specifications;
- evaluation runs and metrics;
- calibration, slices, and baseline/challenger comparisons;
- deterministic findings and diagnostics;
- optional AI-generated explanation/suggestions built on measured evidence;
- registry and champion/challenger promotion decisions;
- CLI/API interfaces and, later, local/self-hosted connectors.

Consumer applications keep their own domain-specific ingestion, feature engineering, ground-truth resolution, product behavior, and UI. Fantasy Premier League forecasting is the first planned consumer and proving ground, not a dependency of this repository.

## Engineering platform

This repository consumes the shared standards from `JCDevBot/engineering-platform` through the pinned release recorded in [`engineering-platform.yaml`](engineering-platform.yaml).

Current adopted release:

- tag: `v0.1.0`
- commit: `1b09e08b2f6a771bc6b8e0c5359dfb2b8a5b71db`

Repository-local ML/AI architecture and autonomy rules live here. Shared engineering policy remains owned by the Engineering Platform and is upgraded through an explicit tested adoption change.

## Agent startup

A new agent should read, in order:

1. this README;
2. `engineering-platform.yaml`;
3. `AGENTS.md`;
4. `ROADMAP.md`;
5. `CURRENT.md`;
6. the active GitHub issue;
7. relevant files under `docs/architecture/`.

GitHub issues and pull requests are the durable work state. Do not rely on prior conversation context when repository state is available.

## Development flow

- `main` — accepted/released state;
- `develop` — integration branch;
- `agent/issue-<number>-<slug>` — ordinary implementation branch from `develop`;
- ordinary PRs target `develop`;
- promotion from `develop` to `main` requires explicit human approval.

The repository owner authorizes autonomous work for decisions that are reversible, local to an accepted issue, testable, and outside the human gates documented in `AGENTS.md`.

## Tooling

Initial toolchain:

- Python 3.12
- `mise` for tool/task entry points
- `uv` for dependency/environment management
- `pytest` for deterministic tests

Setup:

```bash
mise install
mise run setup
```

Standard validation:

```bash
mise run check
```

Individual tests:

```bash
mise run test
```

## Architecture

Start with [`docs/architecture/0001-platform-boundaries.md`](docs/architecture/0001-platform-boundaries.md).

The initial architecture deliberately separates:

```text
Dataset registry
      │
Candidate adapters
      │
Experiment specification
      │
Evaluation engine
      │
Metrics + deterministic findings
      │
Registry / promotion policy
      │
CLI / API
      │
Later: connectors + hosted control plane
```

An LLM may explain findings or propose experiments, but deterministic metric calculation and policy-gated promotion remain authoritative where objective evidence exists.

## Roadmap

See [`ROADMAP.md`](ROADMAP.md). The first implementation milestone after bootstrap is the domain-neutral contract layer and local artifact registry.

## Status

Bootstrap / pre-alpha.
