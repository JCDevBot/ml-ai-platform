from datetime import UTC, datetime
from math import isclose

import pytest

from ml_ai_platform.contracts import CandidateRef, DatasetRef, MetricDirection, MetricResult
from ml_ai_platform.evaluation import (
    EvaluationContext,
    EvaluationError,
    MetricGate,
    assess_challenger,
    classification_metrics,
    comparison_findings,
    probability_metrics,
    regression_metrics,
    sliced_metrics,
)


def context(candidate_id: str = "challenger", namespace: str = "test") -> EvaluationContext:
    now = datetime(2026, 8, 24, 12, tzinfo=UTC)
    return EvaluationContext(
        dataset=DatasetRef(
            dataset_id="fixture",
            version="1",
            source="test",
            schema_id="binary-v1",
            content_hash="abc123",
            created_at=now,
            as_of=now,
        ),
        candidate=CandidateRef(
            candidate_id=candidate_id,
            version="1",
            adapter="deterministic-test",
            created_at=now,
            code_ref="deadbeef",
            config_hash="cfg",
        ),
        namespace=namespace,
    )


def by_name(metrics):
    return {metric.name: metric for metric in metrics}


def test_regression_metrics_known_answers_and_lineage():
    metrics = by_name(regression_metrics(context(), [1, 2, 3], [1, 4, 2]))

    assert metrics["mae"].value == pytest.approx(1.0)
    assert metrics["rmse"].value == pytest.approx((5 / 3) ** 0.5)
    assert metrics["mae"].direction == MetricDirection.MINIMIZE
    assert metrics["mae"].metadata["dataset_id"] == "fixture"
    assert metrics["mae"].metadata["candidate_id"] == "challenger"


def test_classification_metrics_known_confusion_matrix():
    metrics = by_name(classification_metrics(context(), [1, 1, 0, 0], [1, 0, 1, 0]))

    assert metrics["precision"].value == 0.5
    assert metrics["recall"].value == 0.5
    assert metrics["f1"].value == 0.5
    assert metrics["confusion_tp"].value == 1
    assert metrics["confusion_fp"].value == 1
    assert metrics["confusion_fn"].value == 1
    assert metrics["confusion_tn"].value == 1


def test_probability_metrics_brier_log_loss_and_calibration():
    metrics = by_name(probability_metrics(context(), [1, 0], [0.8, 0.2], bins=2))

    assert metrics["brier_score"].value == pytest.approx(0.04)
    assert metrics["log_loss"].value == pytest.approx(-0.5 * (2 * __import__("math").log(0.8)))
    assert metrics["calibration_error"].value == pytest.approx(0.2)
    assert metrics["calibration_error"].metadata["bins"]


def test_sliced_metrics_preserve_first_seen_slice_order():
    metrics = sliced_metrics(
        regression_metrics,
        context(),
        [1, 2, 3, 4],
        [2, 2, 2, 5],
        ["west", "east", "west", "east"],
    )

    assert [metric.slice_id for metric in metrics] == ["west", "west", "east", "east"]
    west = by_name(metrics[:2])
    east = by_name(metrics[2:])
    assert west["mae"].value == 1.0
    assert east["mae"].value == 0.5


def test_comparison_findings_reference_exact_metric_evidence():
    baseline = regression_metrics(context("baseline", "baseline"), [1, 2], [2, 3])
    challenger = regression_metrics(context("challenger", "challenger"), [1, 2], [1, 2])

    findings = comparison_findings(baseline, challenger)

    assert {finding.kind for finding in findings} == {"improvement"}
    mae = next(finding for finding in findings if finding.evidence["metric_name"] == "mae")
    assert mae.metric_ids == (baseline[0].metric_id, challenger[0].metric_id)
    assert mae.evidence["baseline_value"] == 1.0
    assert mae.evidence["challenger_value"] == 0.0


def test_headline_improvement_can_be_rejected_by_protected_slice_regression():
    baseline_context = context("baseline", "baseline")
    challenger_context = context("challenger", "challenger")

    baseline = (
        *regression_metrics(baseline_context, [0, 0], [2, 2]),
        *regression_metrics(baseline_context, [0, 0], [2, 2], slice_id="protected"),
    )
    challenger = (
        *regression_metrics(challenger_context, [0, 0], [1.5, 1.5]),
        *regression_metrics(challenger_context, [0, 0], [2.5, 2.5], slice_id="protected"),
    )

    assessment = assess_challenger(
        baseline,
        challenger,
        gates=(MetricGate("mae", slice_id="protected", max_regression=0.1, protected_slice=True),),
    )

    overall = next(
        finding for finding in assessment.findings
        if finding.kind == "improvement" and finding.evidence["metric_name"] == "mae" and finding.evidence["slice_id"] is None
    )
    protected = next(finding for finding in assessment.findings if finding.kind == "protected_slice_regression")

    assert overall.evidence["challenger_value"] < overall.evidence["baseline_value"]
    assert assessment.eligible is False
    assert protected.metric_ids
    assert protected.evidence["max_regression"] == 0.1
    assert assessment.rejection_reasons


def test_calibration_threshold_violation_has_specialized_finding():
    baseline = (
        MetricResult("baseline:cal", "calibration_error", 0.03, MetricDirection.MINIMIZE),
    )
    challenger = (
        MetricResult("challenger:cal", "calibration_error", 0.08, MetricDirection.MINIMIZE),
    )

    assessment = assess_challenger(
        baseline,
        challenger,
        gates=(MetricGate("calibration_error", max_value=0.05),),
    )

    assert assessment.eligible is False
    finding = next(item for item in assessment.findings if item.kind == "calibration_failure")
    assert finding.metric_ids == (baseline[0].metric_id, challenger[0].metric_id)


def test_invalid_inputs_are_rejected_deterministically():
    with pytest.raises(EvaluationError, match="lengths must match"):
        regression_metrics(context(), [1], [1, 2])

    with pytest.raises(EvaluationError, match="between 0 and 1"):
        probability_metrics(context(), [1], [1.2])

    with pytest.raises(EvaluationError, match="at least one limit"):
        MetricGate("mae")
