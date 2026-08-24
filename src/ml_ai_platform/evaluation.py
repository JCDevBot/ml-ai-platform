"""Deterministic evaluators and evidence-based challenger assessment.

This module deliberately accepts plain observations plus the platform's core
``DatasetRef``/``CandidateRef`` contracts.  Consumers remain responsible for
producing predictions and domain-specific labels; the platform owns reusable
measurement and comparison mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from typing import Callable, Hashable, Mapping, Sequence

from .contracts import CandidateRef, DatasetRef, Finding, MetricDirection, MetricResult


class EvaluationError(ValueError):
    """Raised when evaluation inputs are invalid or incomplete."""


Number = int | float


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Lineage required to attach measurements to a dataset and candidate."""

    dataset: DatasetRef
    candidate: CandidateRef
    namespace: str = "evaluation"

    def __post_init__(self) -> None:
        if not self.namespace.strip():
            raise EvaluationError("namespace must be non-empty")


@dataclass(frozen=True, slots=True)
class MetricGate:
    """A deterministic threshold/comparison gate for one metric and slice."""

    metric_name: str
    slice_id: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    max_regression: float | None = None
    protected_slice: bool = False

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise EvaluationError("metric_name must be non-empty")
        if self.min_value is None and self.max_value is None and self.max_regression is None:
            raise EvaluationError("a metric gate must define at least one limit")
        if self.max_regression is not None and self.max_regression < 0:
            raise EvaluationError("max_regression cannot be negative")


@dataclass(frozen=True, slots=True)
class ChallengerAssessment:
    """Deterministic eligibility result derived entirely from measured evidence."""

    eligible: bool
    findings: tuple[Finding, ...]
    rejection_reasons: tuple[str, ...]


def _validate_pair(y_true: Sequence[Number], y_pred: Sequence[Number]) -> None:
    if len(y_true) != len(y_pred):
        raise EvaluationError("truth and prediction lengths must match")
    if not y_true:
        raise EvaluationError("evaluation requires at least one observation")
    for value in (*y_true, *y_pred):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EvaluationError("numeric evaluation inputs must contain only numbers")


def _metric_id(context: EvaluationContext, name: str, slice_id: str | None) -> str:
    suffix = f":slice={slice_id}" if slice_id is not None else ""
    return f"{context.namespace}:{context.candidate.candidate_id}:{context.candidate.version}:{name}{suffix}"


def _metadata(context: EvaluationContext) -> dict[str, str]:
    return {
        "dataset_id": context.dataset.dataset_id,
        "dataset_version": context.dataset.version,
        "candidate_id": context.candidate.candidate_id,
        "candidate_version": context.candidate.version,
    }


def regression_metrics(
    context: EvaluationContext,
    y_true: Sequence[Number],
    y_pred: Sequence[Number],
    *,
    slice_id: str | None = None,
) -> tuple[MetricResult, ...]:
    """Calculate deterministic MAE and RMSE metrics."""

    _validate_pair(y_true, y_pred)
    errors = [float(pred) - float(truth) for truth, pred in zip(y_true, y_pred, strict=True)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = sqrt(sum(error * error for error in errors) / len(errors))
    metadata = _metadata(context)
    return (
        MetricResult(
            metric_id=_metric_id(context, "mae", slice_id),
            name="mae",
            value=mae,
            direction=MetricDirection.MINIMIZE,
            slice_id=slice_id,
            metadata=metadata,
        ),
        MetricResult(
            metric_id=_metric_id(context, "rmse", slice_id),
            name="rmse",
            value=rmse,
            direction=MetricDirection.MINIMIZE,
            slice_id=slice_id,
            metadata=metadata,
        ),
    )


def classification_metrics(
    context: EvaluationContext,
    y_true: Sequence[Hashable],
    y_pred: Sequence[Hashable],
    *,
    positive_label: Hashable = 1,
    slice_id: str | None = None,
) -> tuple[MetricResult, ...]:
    """Calculate binary precision/recall/F1 and confusion-matrix cells."""

    if len(y_true) != len(y_pred):
        raise EvaluationError("truth and prediction lengths must match")
    if not y_true:
        raise EvaluationError("evaluation requires at least one observation")

    tp = sum(t == positive_label and p == positive_label for t, p in zip(y_true, y_pred, strict=True))
    fp = sum(t != positive_label and p == positive_label for t, p in zip(y_true, y_pred, strict=True))
    fn = sum(t == positive_label and p != positive_label for t, p in zip(y_true, y_pred, strict=True))
    tn = len(y_true) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    metadata = {**_metadata(context), "positive_label": str(positive_label)}

    specs = (
        ("precision", precision, MetricDirection.MAXIMIZE),
        ("recall", recall, MetricDirection.MAXIMIZE),
        ("f1", f1, MetricDirection.MAXIMIZE),
        ("confusion_tp", float(tp), MetricDirection.NEUTRAL),
        ("confusion_fp", float(fp), MetricDirection.NEUTRAL),
        ("confusion_fn", float(fn), MetricDirection.NEUTRAL),
        ("confusion_tn", float(tn), MetricDirection.NEUTRAL),
    )
    return tuple(
        MetricResult(
            metric_id=_metric_id(context, name, slice_id),
            name=name,
            value=value,
            direction=direction,
            slice_id=slice_id,
            metadata=metadata,
        )
        for name, value, direction in specs
    )


def probability_metrics(
    context: EvaluationContext,
    y_true: Sequence[int],
    probabilities: Sequence[Number],
    *,
    bins: int = 10,
    epsilon: float = 1e-15,
    slice_id: str | None = None,
) -> tuple[MetricResult, ...]:
    """Calculate binary Brier score, log loss, and ECE calibration summary."""

    _validate_pair(y_true, probabilities)
    if bins <= 0:
        raise EvaluationError("bins must be positive")
    if not 0 < epsilon < 0.5:
        raise EvaluationError("epsilon must be between 0 and 0.5")
    if any(value not in (0, 1) for value in y_true):
        raise EvaluationError("probability truth labels must be 0 or 1")
    probs = [float(value) for value in probabilities]
    if any(value < 0 or value > 1 for value in probs):
        raise EvaluationError("probabilities must be between 0 and 1")

    n = len(probs)
    brier = sum((prob - truth) ** 2 for truth, prob in zip(y_true, probs, strict=True)) / n
    clipped = [min(1 - epsilon, max(epsilon, prob)) for prob in probs]
    log_loss = -sum(
        truth * log(prob) + (1 - truth) * log(1 - prob)
        for truth, prob in zip(y_true, clipped, strict=True)
    ) / n

    bin_rows: list[dict[str, float | int]] = []
    ece = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        positions = [
            i for i, prob in enumerate(probs)
            if prob >= low and (prob < high or (index == bins - 1 and prob <= high))
        ]
        if not positions:
            continue
        confidence = sum(probs[i] for i in positions) / len(positions)
        observed = sum(y_true[i] for i in positions) / len(positions)
        weight = len(positions) / n
        ece += weight * abs(confidence - observed)
        bin_rows.append(
            {
                "lower": low,
                "upper": high,
                "count": len(positions),
                "mean_probability": confidence,
                "observed_rate": observed,
            }
        )

    metadata = _metadata(context)
    return (
        MetricResult(
            metric_id=_metric_id(context, "brier_score", slice_id),
            name="brier_score",
            value=brier,
            direction=MetricDirection.MINIMIZE,
            slice_id=slice_id,
            metadata=metadata,
        ),
        MetricResult(
            metric_id=_metric_id(context, "log_loss", slice_id),
            name="log_loss",
            value=log_loss,
            direction=MetricDirection.MINIMIZE,
            slice_id=slice_id,
            metadata=metadata,
        ),
        MetricResult(
            metric_id=_metric_id(context, "calibration_error", slice_id),
            name="calibration_error",
            value=ece,
            direction=MetricDirection.MINIMIZE,
            slice_id=slice_id,
            metadata={**metadata, "bins": bin_rows},
        ),
    )


def sliced_metrics(
    evaluator: Callable[..., tuple[MetricResult, ...]],
    context: EvaluationContext,
    y_true: Sequence[object],
    y_pred: Sequence[object],
    slices: Sequence[str],
    **kwargs: object,
) -> tuple[MetricResult, ...]:
    """Run an evaluator once per named slice in deterministic first-seen order."""

    if len(y_true) != len(y_pred) or len(y_true) != len(slices):
        raise EvaluationError("truth, prediction, and slice lengths must match")
    ordered = list(dict.fromkeys(slices))
    results: list[MetricResult] = []
    for slice_id in ordered:
        positions = [index for index, value in enumerate(slices) if value == slice_id]
        truth_slice = [y_true[index] for index in positions]
        pred_slice = [y_pred[index] for index in positions]
        results.extend(evaluator(context, truth_slice, pred_slice, slice_id=slice_id, **kwargs))
    return tuple(results)


def _metric_map(metrics: Sequence[MetricResult]) -> dict[tuple[str, str | None], MetricResult]:
    result: dict[tuple[str, str | None], MetricResult] = {}
    for metric in metrics:
        key = (metric.name, metric.slice_id)
        if key in result:
            raise EvaluationError(f"duplicate metric for {metric.name!r} slice {metric.slice_id!r}")
        result[key] = metric
    return result


def _adverse_delta(baseline: MetricResult, challenger: MetricResult) -> float:
    if baseline.direction != challenger.direction:
        raise EvaluationError(f"metric direction mismatch for {baseline.name}")
    if challenger.direction == MetricDirection.MINIMIZE:
        return challenger.value - baseline.value
    if challenger.direction == MetricDirection.MAXIMIZE:
        return baseline.value - challenger.value
    return 0.0


def comparison_findings(
    baseline_metrics: Sequence[MetricResult],
    challenger_metrics: Sequence[MetricResult],
) -> tuple[Finding, ...]:
    """Produce structured improvement/regression findings for matched metrics."""

    baseline = _metric_map(baseline_metrics)
    challenger = _metric_map(challenger_metrics)
    findings: list[Finding] = []
    for key in sorted(set(baseline) & set(challenger), key=lambda item: (item[0], item[1] or "")):
        left = baseline[key]
        right = challenger[key]
        if right.direction == MetricDirection.NEUTRAL or right.value == left.value:
            continue
        adverse = _adverse_delta(left, right)
        kind = "regression" if adverse > 0 else "improvement"
        severity = "warning" if adverse > 0 else "info"
        findings.append(
            Finding(
                finding_id=f"compare:{right.metric_id}",
                kind=kind,
                severity=severity,
                message=f"{right.name} {kind} versus baseline",
                metric_ids=(left.metric_id, right.metric_id),
                evidence={
                    "metric_name": right.name,
                    "slice_id": right.slice_id,
                    "baseline_value": left.value,
                    "challenger_value": right.value,
                    "adverse_delta": adverse,
                    "direction": right.direction.value,
                },
            )
        )
    return tuple(findings)


def assess_challenger(
    baseline_metrics: Sequence[MetricResult],
    challenger_metrics: Sequence[MetricResult],
    gates: Sequence[MetricGate],
) -> ChallengerAssessment:
    """Apply deterministic threshold/regression gates to a challenger."""

    baseline = _metric_map(baseline_metrics)
    challenger = _metric_map(challenger_metrics)
    findings = list(comparison_findings(baseline_metrics, challenger_metrics))
    rejection_reasons: list[str] = []

    for index, gate in enumerate(gates):
        key = (gate.metric_name, gate.slice_id)
        metric = challenger.get(key)
        if metric is None:
            reason = f"missing required metric {gate.metric_name} slice={gate.slice_id!r}"
            rejection_reasons.append(reason)
            findings.append(
                Finding(
                    finding_id=f"gate:{index}:missing",
                    kind="threshold_violation",
                    severity="error",
                    message=reason,
                    evidence={"metric_name": gate.metric_name, "slice_id": gate.slice_id},
                )
            )
            continue

        violations: list[str] = []
        if gate.min_value is not None and metric.value < gate.min_value:
            violations.append(f"value {metric.value} is below minimum {gate.min_value}")
        if gate.max_value is not None and metric.value > gate.max_value:
            violations.append(f"value {metric.value} exceeds maximum {gate.max_value}")
        base_metric = baseline.get(key)
        adverse = None
        if gate.max_regression is not None:
            if base_metric is None:
                violations.append("baseline metric required for regression gate is missing")
            else:
                adverse = _adverse_delta(base_metric, metric)
                if adverse > gate.max_regression:
                    violations.append(f"adverse delta {adverse} exceeds maximum regression {gate.max_regression}")

        if not violations:
            continue
        reason = f"{gate.metric_name} slice={gate.slice_id!r}: " + "; ".join(violations)
        rejection_reasons.append(reason)
        kind = "protected_slice_regression" if gate.protected_slice and adverse is not None and adverse > 0 else (
            "calibration_failure" if gate.metric_name == "calibration_error" else "threshold_violation"
        )
        metric_ids = (metric.metric_id,) if base_metric is None else (base_metric.metric_id, metric.metric_id)
        findings.append(
            Finding(
                finding_id=f"gate:{index}:{metric.metric_id}",
                kind=kind,
                severity="error",
                message=reason,
                metric_ids=metric_ids,
                evidence={
                    "metric_name": gate.metric_name,
                    "slice_id": gate.slice_id,
                    "challenger_value": metric.value,
                    "baseline_value": base_metric.value if base_metric else None,
                    "max_regression": gate.max_regression,
                    "min_value": gate.min_value,
                    "max_value": gate.max_value,
                    "protected_slice": gate.protected_slice,
                },
            )
        )

    return ChallengerAssessment(
        eligible=not rejection_reasons,
        findings=tuple(findings),
        rejection_reasons=tuple(rejection_reasons),
    )
