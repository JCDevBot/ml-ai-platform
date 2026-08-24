"""Local CLI workflow built on the platform contracts, registry, and evaluators."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .cli_io import CLI_SCHEMA_VERSION, CliError
from .contracts import CandidateRef, DatasetRef, EvaluationRun, ExperimentSpec, RecordRef, canonical_json, content_identity
from .evaluation import (
    EvaluationContext,
    MetricGate,
    assess_challenger,
    classification_metrics,
    comparison_findings,
    probability_metrics,
    regression_metrics,
    sliced_metrics,
)
from .registry import FilesystemRegistry, RecordAlreadyExists, registry_relative_path


def _now() -> datetime:
    return datetime.now(UTC)


def _record(record: Any) -> dict[str, Any]:
    return record.to_dict()


def _ref(data: Mapping[str, Any], kind: str) -> RecordRef:
    key = f"{kind}_id"
    try:
        return RecordRef(id=str(data[key]), version=str(data["version"]))
    except KeyError as exc:
        raise CliError(f"{kind} reference requires {key} and version") from exc


def _put(registry: FilesystemRegistry, record: Any) -> Path:
    try:
        return registry.put(record)
    except RecordAlreadyExists:
        relative = registry_relative_path(record)
        existing = registry.get(relative)
        if canonical_json(existing) != canonical_json(record):
            raise CliError(f"registry key already exists with different content: {relative}")
        return registry.root / relative


def register_dataset(registry: FilesystemRegistry, document: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(document)
    payload.pop("record_type", None)
    payload.setdefault("created_at", _now().isoformat())
    dataset = DatasetRef.from_dict(payload)
    path = _put(registry, dataset)
    return {"record": _record(dataset), "registry_path": str(path.relative_to(registry.root))}


def register_candidate(registry: FilesystemRegistry, document: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(document)
    payload.pop("record_type", None)
    payload.setdefault("created_at", _now().isoformat())
    candidate = CandidateRef.from_dict(payload)
    path = _put(registry, candidate)
    return {"record": _record(candidate), "registry_path": str(path.relative_to(registry.root))}


def _gate(data: Mapping[str, Any]) -> MetricGate:
    if "metric_name" not in data:
        raise CliError("metric gate requires metric_name")
    return MetricGate(
        metric_name=str(data["metric_name"]),
        slice_id=data.get("slice_id"),
        min_value=data.get("min_value"),
        max_value=data.get("max_value"),
        max_regression=data.get("max_regression"),
        protected_slice=bool(data.get("protected_slice", False)),
    )


def _metrics(
    task: str,
    context: EvaluationContext,
    truth: Sequence[Any],
    predictions: Sequence[Any],
    slices: Sequence[str] | None,
    options: Mapping[str, Any],
):
    evaluators = {
        "regression": regression_metrics,
        "classification": classification_metrics,
        "probability": probability_metrics,
    }
    if task not in evaluators:
        raise CliError(f"unsupported evaluation task: {task!r}")
    evaluator = evaluators[task]
    kwargs: dict[str, Any] = {}
    if task == "classification" and "positive_label" in options:
        kwargs["positive_label"] = options["positive_label"]
    if task == "probability":
        if "bins" in options:
            kwargs["bins"] = int(options["bins"])
        if "epsilon" in options:
            kwargs["epsilon"] = float(options["epsilon"])
    result = list(evaluator(context, truth, predictions, **kwargs))
    if slices is not None:
        result.extend(sliced_metrics(evaluator, context, truth, predictions, slices, **kwargs))
    return tuple(result)


def _experiment(
    document: Mapping[str, Any], dataset: DatasetRef, candidate: CandidateRef, created_at: datetime
) -> ExperimentSpec:
    value = document.get("experiment")
    if not isinstance(value, Mapping):
        raise CliError("evaluation document requires an experiment object")
    evaluator_ids = value.get("evaluator_ids") or [str(document.get("task", ""))]
    try:
        return ExperimentSpec(
            experiment_id=str(value["experiment_id"]),
            version=str(value["version"]),
            dataset_refs=(dataset.ref,),
            candidate_refs=(candidate.ref,),
            evaluator_ids=tuple(str(item) for item in evaluator_ids),
            created_at=created_at,
            baseline_candidate_refs=tuple(_ref(item, "candidate") for item in value.get("baseline_candidate_refs", ())),
            slice_ids=tuple(str(item) for item in value.get("slice_ids", ())),
            policy_version=value.get("policy_version"),
            code_ref=value.get("code_ref"),
            config_hash=value.get("config_hash"),
            metadata=dict(value.get("metadata", {})),
        )
    except KeyError as exc:
        raise CliError("experiment requires experiment_id and version") from exc


def evaluate(registry: FilesystemRegistry, document: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    try:
        dataset_ref = _ref(document["dataset"], "dataset")
        candidate_ref = _ref(document["candidate"], "candidate")
        run_id = str(document["run_id"])
        task = str(document["task"])
        truth = document["truth"]
        predictions = document["predictions"]
    except (KeyError, TypeError) as exc:
        raise CliError("evaluation requires dataset, candidate, run_id, task, truth, and predictions") from exc
    if not isinstance(truth, list) or not isinstance(predictions, list):
        raise CliError("truth and predictions must be arrays")
    slices = document.get("slices")
    if slices is not None and not isinstance(slices, list):
        raise CliError("slices must be an array")
    options = document.get("options", {})
    if not isinstance(options, Mapping):
        raise CliError("options must be an object")

    dataset = registry.get_dataset(dataset_ref.id, dataset_ref.version)
    candidate = registry.get_candidate(candidate_ref.id, candidate_ref.version)
    started = _now()
    experiment = _experiment(document, dataset, candidate, started)
    _put(registry, experiment)
    context = EvaluationContext(dataset=dataset, candidate=candidate, namespace=run_id)
    metrics = _metrics(task, context, truth, predictions, slices, options)
    run = EvaluationRun(
        run_id=run_id,
        experiment_ref=experiment.ref,
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        started_at=started,
        completed_at=_now(),
        code_ref=str(document.get("code_ref") or candidate.code_ref or experiment.code_ref or "local"),
        config_hash=str(document.get("config_hash") or content_identity(document)),
        metrics=metrics,
        metadata={"task": task, "cli_schema_version": CLI_SCHEMA_VERSION},
    )
    _put(registry, run)

    response: dict[str, Any] = {"run": _record(run), "eligible": True, "rejection_reasons": []}
    baseline_id = document.get("baseline_run_id")
    gates_value = document.get("gates", ())
    if gates_value and not baseline_id:
        raise CliError("gates require baseline_run_id")
    if baseline_id:
        baseline = registry.get_evaluation_run(str(baseline_id))
        gates = tuple(_gate(item) for item in gates_value)
        assessment = assess_challenger(baseline.metrics, run.metrics, gates)
        response.update(
            eligible=assessment.eligible,
            rejection_reasons=list(assessment.rejection_reasons),
            findings=[_record(item) for item in assessment.findings],
        )
        return response, assessment.eligible
    return response, True


def compare(
    registry: FilesystemRegistry,
    baseline_run_id: str,
    challenger_run_id: str,
    gate_document: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    baseline = registry.get_evaluation_run(baseline_run_id)
    challenger = registry.get_evaluation_run(challenger_run_id)
    if gate_document is not None:
        values = gate_document.get("gates")
        if not isinstance(values, list):
            raise CliError("gate document requires a gates array")
        assessment = assess_challenger(baseline.metrics, challenger.metrics, tuple(_gate(item) for item in values))
        findings = assessment.findings
        eligible = assessment.eligible
        reasons = assessment.rejection_reasons
    else:
        findings = comparison_findings(baseline.metrics, challenger.metrics)
        eligible = True
        reasons = ()
    return {
        "baseline_run_id": baseline.run_id,
        "challenger_run_id": challenger.run_id,
        "eligible": eligible,
        "rejection_reasons": list(reasons),
        "findings": [_record(item) for item in findings],
    }, eligible


def report(registry: FilesystemRegistry, run_id: str) -> dict[str, Any]:
    run = registry.get_evaluation_run(run_id)
    metrics = sorted(run.metrics, key=lambda item: (item.slice_id or "", item.name))
    return {
        "run_id": run.run_id,
        "experiment": {"id": run.experiment_ref.id, "version": run.experiment_ref.version},
        "candidates": [{"id": item.id, "version": item.version} for item in run.candidate_refs],
        "datasets": [{"id": item.id, "version": item.version} for item in run.dataset_refs],
        "metrics": [_record(item) for item in metrics],
        "findings": [_record(item) for item in run.findings],
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
