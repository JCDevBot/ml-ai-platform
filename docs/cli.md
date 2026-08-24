# Local CLI

The `mlai` CLI is the local-first developer interface to the platform. It uses the same contracts, filesystem registry, and deterministic evaluation engine as the Python API and does not require a network service.

## Output contract

JSON is the default output format. Every command emits one stable envelope:

```json
{"command":"report","data":{},"ok":true,"schema_version":"mlai.cli.v1"}
```

Consumers should branch on `schema_version`, `ok`, and command-specific fields under `data`. Human-readable output is available with `--output text`.

Exit codes:

- `0` — command succeeded and any configured policy gates passed;
- `2` — invalid input, missing registry data, or another command error;
- `3` — evaluation/comparison completed, but deterministic policy gates rejected the challenger.

Errors are also emitted in the versioned envelope with `data.error_type` and `data.message`.

## Registry

The default registry is `.mlai`. Override it per invocation:

```bash
mlai --registry ./artifacts/mlai dataset register dataset.yaml
```

Registry writes use the immutable filesystem registry. Re-registering byte-equivalent contract content is idempotent; attempting to reuse an identity/version for different content fails.

## Register a dataset

```yaml
# dataset.yaml
dataset_id: points-history
version: "1"
source: local-export
schema_id: points-v1
content_hash: sha256:abc123
created_at: "2026-08-24T18:00:00+00:00"
as_of: "2026-08-24T17:00:00+00:00"
```

```bash
mlai dataset register dataset.yaml
```

## Register a candidate

```yaml
# candidate.yaml
candidate_id: player-points
version: "7"
adapter: generic-python
created_at: "2026-08-24T18:00:00+00:00"
artifact_uri: ./models/player-points-v7.pkl
code_ref: a1b2c3d
```

```bash
mlai candidate register candidate.yaml
```

The core does not load or execute the candidate artifact. A consumer or adapter produces predictions; `mlai` evaluates those predictions reproducibly.

## Evaluate

```yaml
# experiment.yaml
run_id: points-v7-backtest
task: regression

dataset:
  dataset_id: points-history
  version: "1"

candidate:
  candidate_id: player-points
  version: "7"

experiment:
  experiment_id: player-points-backtest
  version: "7"
  slice_ids: [midfielder, defender]

truth: [3.0, 6.0, 2.0, 8.0]
predictions: [3.5, 5.5, 4.0, 7.0]
slices: [midfielder, midfielder, defender, defender]
code_ref: a1b2c3d
```

```bash
mlai evaluate experiment.yaml
```

Supported initial tasks are `regression`, `classification`, and `probability`. Overall metrics are always produced; when `slices` is supplied, the same evaluator also runs per slice.

Classification accepts `options.positive_label`. Probability evaluation accepts `options.bins` and `options.epsilon`.

## Compare and gate

Without gates, comparison emits deterministic improvement/regression findings:

```bash
mlai compare baseline-run challenger-run
```

A gate document can make the comparison CI-enforceable:

```yaml
# gates.yaml
gates:
  - metric_name: mae
    slice_id: defender
    max_regression: 0.25
    protected_slice: true
  - metric_name: calibration_error
    max_value: 0.05
```

```bash
mlai compare baseline-run challenger-run --gates gates.yaml
```

A rejected challenger returns exit code `3`; deterministic evidence remains available in the JSON response.

An evaluation document may also include `baseline_run_id` and `gates` to apply the same policy assessment immediately after scoring.

## Report

```bash
mlai report points-v7-backtest
```

The report command returns recorded lineage, timestamps, metrics, and findings for the immutable evaluation run.
