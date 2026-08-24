# Platform boundaries

Date: 2026-08-24
Status: proposed

## Context

The platform must support classical ML, forecasting, LLM, RAG, and agentic systems without becoming a framework-specific monolith or embedding consumer-domain behavior such as Fantasy Premier League logic.

It must also support an eventual hosted service and local/self-hosted connectors without making remote infrastructure the first implementation problem.

## Decision

Use a contract-and-adapter architecture with six core layers.

### 1. Dataset layer

Owns identity and lineage for data used in training/evaluation.

Minimum metadata:

- stable dataset ID
- version
- source identity
- schema identity
- content hash or equivalent immutable identity
- created timestamp
- `as_of` timestamp where temporal leakage matters
- feature/config version when applicable
- parent/source lineage

Raw data storage is an implementation detail. A dataset may be local-only while the platform stores metadata and evaluation results.

### 2. Candidate layer

Represents the system being evaluated. A candidate is intentionally broader than a trained model.

Examples:

- scikit-learn/XGBoost model
- PyTorch model
- HTTP inference endpoint
- LLM + prompt
- RAG pipeline
- tool-using agent
- ensemble/router
- deterministic baseline

The core interacts through small adapter interfaces rather than importing every provider/framework.

### 3. Experiment/evaluation layer

An experiment binds dataset(s), candidate(s), evaluator configuration, baselines, slices, and policy thresholds.

Evaluation produces immutable metric/artifact references rather than mutating candidate state.

### 4. Findings/analysis layer

Deterministic code converts measurements into structured findings such as:

- improvement/regression vs baseline
- protected-slice regression
- calibration failure
- drift warning
- threshold violation
- missing lineage/reproducibility warning

Optional LLM reasoning may summarize findings or propose experiments, but must consume measured findings and remain clearly distinguishable from deterministic evidence.

### 5. Registry/promotion layer

Stores candidate versions and lifecycle state. Promotion decisions reference exact evaluation evidence and policy version.

Initial promotion is local and human-approved where configured. Future consumers may allow automatic promotion when deterministic policy gates are proven sufficient.

### 6. Interface/connectivity layer

Initial interface: local CLI and Python API.

Later interfaces:

- HTTP API/control plane
- CI integration
- local connector
- self-hosted connector/runner

Connectors initiate outbound authenticated connections. The hosted platform does not require inbound access to a user's machine or private network.

## Trust and data-movement modes

Future connectors must support explicit per-source policy:

1. `metadata-only` — hashes, lineage, metrics, configuration; raw records remain local.
2. `upload` — explicitly approved datasets/artifacts may be transferred.
3. `local-execution` — evaluation job executes in the user's environment and returns bounded results/artifacts.

No mode may imply unrestricted filesystem ingestion. Paths/scopes are allow-listed and secrets/private paths are excluded by default.

## Consumer boundary

Consumers own domain-specific behavior.

For FPL, the consumer owns API ingestion, leakage-safe feature engineering, market/question generation, scoring resolution, and UI. The ML/AI platform owns reusable dataset/candidate/evaluation/findings/registry mechanics.

## Consequences

Benefits:

- one lifecycle can evaluate heterogeneous candidate types;
- FPL can prove the abstractions without contaminating them;
- local-first development avoids premature hosted infrastructure;
- privacy-sensitive users can keep data local;
- deterministic evidence stays separate from generative explanation.

Costs:

- adapter interfaces require careful versioning;
- some evaluator behavior is necessarily task-specific and must be registered rather than hidden in a universal evaluator;
- lineage and immutable evaluation records add discipline before the UI becomes sophisticated.

## Alternatives considered

### Build directly inside the FPL application

Rejected because it would couple lifecycle abstractions to one domain and make LLM/agent evaluation awkward later.

### Start with a hosted connector/control plane

Rejected because it would emphasize infrastructure before proving evaluation value.

### Make an LLM the central evaluator/decision-maker

Rejected because deterministic metrics, reproducibility, and promotion policy must remain authoritative where objective ground truth exists.

## Migration and validation

Phase 1 implements only local contracts and a filesystem-backed registry. The architecture is considered validated when at least two materially different consumers/candidate types can use the same core without domain branching in core modules.
