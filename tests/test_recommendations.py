from __future__ import annotations

from ml_ai_platform.contracts import Finding, MetricDirection, MetricResult
from ml_ai_platform.evaluation import MetricGate, assess_challenger
from ml_ai_platform.recommendations import BoundedSearchSpace, recommend_experiments


def _finding(kind: str, suffix: str) -> Finding:
    return Finding(
        finding_id=f"finding-{suffix}",
        kind=kind,
        severity="error",
        message=f"{kind} evidence",
        metric_ids=(f"metric-{suffix}",),
        evidence={
            "metric_name": "mae" if kind != "calibration_failure" else "calibration_error",
            "slice_id": "protected" if kind == "protected_slice_regression" else None,
            "max_regression": 0.1,
            "min_value": None,
            "max_value": 0.2 if kind in {"calibration_failure", "threshold_violation"} else None,
        },
    )


def test_rule_paths_are_deterministic_and_reference_exact_evidence() -> None:
    findings = (
        _finding("threshold_violation", "threshold"),
        _finding("regression", "regression"),
        _finding("calibration_failure", "calibration"),
        _finding("protected_slice_regression", "slice"),
    )

    first = recommend_experiments(evaluation_run_id="run-42", findings=findings)
    second = recommend_experiments(evaluation_run_id="run-42", findings=tuple(reversed(findings)))

    assert first == second
    assert {item.action for item in first} == {
        "investigate_regression",
        "improve_protected_slice",
        "improve_calibration",
        "improve_threshold_metric",
    }
    assert all(item.evaluation_run_id == "run-42" for item in first)
    assert all(item.rule_id.startswith("finding-kind:") for item in first)
    assert all(item.rule_version == "1" for item in first)
    assert all(len(item.finding_ids) == 1 for item in first)


def test_non_actionable_improvement_is_not_recommended() -> None:
    finding = Finding(
        finding_id="finding-improvement",
        kind="improvement",
        severity="info",
        message="better",
        metric_ids=("metric-a", "metric-b"),
        evidence={"metric_name": "mae"},
    )

    assert recommend_experiments(evaluation_run_id="run-1", findings=[finding]) == ()


def test_bounded_search_is_sorted_and_never_exceeds_trial_limit() -> None:
    search = BoundedSearchSpace(
        choices={
            "learning_rate": (0.01, 0.1),
            "depth": (2, 4, 8),
        },
        max_trials=4,
    )

    assert search.trials() == (
        {"depth": 2, "learning_rate": 0.01},
        {"depth": 2, "learning_rate": 0.1},
        {"depth": 4, "learning_rate": 0.01},
        {"depth": 4, "learning_rate": 0.1},
    )


def test_search_cannot_expand_beyond_configured_choices() -> None:
    search = BoundedSearchSpace(choices={"temperature": (0.0, 0.2)}, max_trials=10)

    trials = search.trials()

    assert trials == ({"temperature": 0.0}, {"temperature": 0.2})
    assert all(trial["temperature"] in (0.0, 0.2) for trial in trials)


def test_rejected_challenger_produces_bounded_next_experiment_recommendation() -> None:
    baseline = (
        MetricResult(
            metric_id="baseline:mae:protected",
            name="mae",
            value=2.0,
            direction=MetricDirection.MINIMIZE,
            slice_id="protected",
        ),
    )
    challenger = (
        MetricResult(
            metric_id="challenger:mae:protected",
            name="mae",
            value=2.5,
            direction=MetricDirection.MINIMIZE,
            slice_id="protected",
        ),
    )
    assessment = assess_challenger(
        baseline,
        challenger,
        [MetricGate(metric_name="mae", slice_id="protected", max_regression=0.1, protected_slice=True)],
    )

    assert not assessment.eligible
    recommendations = recommend_experiments(
        evaluation_run_id="run-rejected-challenger",
        findings=assessment.findings,
    )
    protected = [item for item in recommendations if item.action == "improve_protected_slice"]
    assert len(protected) == 1
    assert protected[0].finding_ids[0].startswith("gate:")
    assert protected[0].parameters["slice_id"] == "protected"
