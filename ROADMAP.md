# ML / AI Platform Roadmap

The roadmap orders capability development. GitHub issues define bounded implementation work and acceptance criteria.

## Phase 0 — Repository foundation

Goal: make the project reproducible, inspectable, and safe for autonomous agent work.

- pinned Engineering Platform adoption
- local steering and human gates
- Python/mise/uv tooling
- deterministic CI
- architecture boundaries
- durable handoff state

Exit: a fresh agent can recover project state and run the standard validation path without conversational context.

## Phase 1 — Core contracts and local artifact registry

Goal: define the smallest domain-neutral contracts needed to represent ML/AI work.

Initial contracts:

- `DatasetRef` / dataset snapshot metadata
- `CandidateRef` / candidate adapter identity
- `ExperimentSpec`
- `EvaluationRun`
- `MetricResult`
- `Finding`
- `PromotionDecision`

Requirements:

- stable IDs and versioned schema
- lineage to code commit, dataset, feature/config version, and candidate artifact
- local filesystem-backed registry first
- deterministic serialization and tests
- no dependency on FPL or a specific model provider

## Phase 2 — Evaluation engine and deterministic findings

Goal: run reproducible evaluations and produce evidence beyond a single headline metric.

Initial evaluators:

- regression: MAE, RMSE
- classification: precision, recall, F1, confusion matrix
- probability forecasts: Brier score, log loss, calibration
- slice evaluation
- latency/cost metadata where available

Initial findings:

- baseline/challenger comparisons
- protected-slice regressions
- calibration regressions
- threshold/policy violations
- dataset/candidate lineage anomalies

LLMs may summarize measured findings but may not replace deterministic scoring.

## Phase 3 — CLI and developer workflow

Goal: make the platform useful from a local repository without a hosted service.

Target workflow:

```text
mlai dataset register ...
mlai candidate register ...
mlai evaluate experiment.yaml
mlai compare <run-a> <run-b>
mlai report <run-id>
```

Add machine-readable JSON output suitable for CI.

## Phase 4 — Registry and champion/challenger lifecycle

Goal: manage evidence-driven model lifecycle decisions.

- candidate/model versions
- champion/challenger aliases or equivalent state
- deterministic promotion policies
- rejection reasons
- reproducible lineage
- human approval gates where configured

Start with local promotion state. Hosted/shared registry comes later.

## Phase 5 — FPL forecasting consumer

Goal: prove the abstractions against a real continuously resolving forecasting problem.

The FPL consumer owns:

- FPL ingestion and historical snapshots
- feature engineering
- leakage-safe temporal backtesting
- player-points and fixture models
- forecast resolution and UI

The ML/AI platform owns:

- dataset/candidate registration
- experiment execution
- metrics and calibration
- findings
- model comparison
- promotion lifecycle

## Phase 6 — Local connector and hosted control plane

Goal: allow developer/team environments to connect without opening inbound access to local networks.

Connector principles:

- outbound authenticated connection from local/self-hosted environment
- explicit configured artifact scopes
- metadata-only, upload, and local-execution modes
- per-connector revocable credentials
- no default recursive filesystem access
- privacy and secret exclusions

Hosted control plane can add organizations, workspaces, subscriptions, schedules, dashboards, and team audit history.

## Phase 7 — LLM, RAG, and agent evaluation

Goal: support generative systems as candidates under the same lifecycle framework.

Candidate types may include:

- model + prompt
- RAG pipeline
- tool-using agent
- agent graph
- ensemble/router

Evaluators may include:

- labeled task accuracy
- tool-selection accuracy
- unsupported-claim rate
- retrieval quality
- structured-output validity
- latency and cost
- model/prompt/config comparisons
- deterministic checks plus optional judge-model evaluation

Judge-model output must remain distinguishable from deterministic ground-truth metrics.

## Phase 8 — Autonomous experiment recommendations

Goal: use accumulated evidence to propose the next bounded experiment.

The platform may:

- detect drift or slice degradation
- generate hypotheses from measured findings
- propose feature/model/config experiments
- run bounded parameter searches
- evaluate and reject challengers automatically

Production promotion remains policy-controlled and human-gated until deterministic promotion criteria are proven trustworthy for the consumer.

## Phase 9 — External forecasting / market adapters

Goal: prove the core can compare internal models, humans, baselines, and external consensus under one forecast contract.

Potential adapters may ingest read-only public prediction-market probabilities. Trading, wallets, or financial execution are explicitly out of scope unless separately approved.
