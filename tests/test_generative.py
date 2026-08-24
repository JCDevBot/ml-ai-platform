from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ml_ai_platform.contracts import CandidateRef, DatasetRef, MetricDirection
from ml_ai_platform.evaluation import EvaluationContext, EvaluationError
from ml_ai_platform.generative import (
    GenerativeCase,
    GenerativeOutput,
    JudgeResult,
    evaluate_generative,
    judge_metrics,
    run_candidate,
)

NOW = datetime(2026, 8, 24, 19, 0, tzinfo=UTC)


def _context() -> EvaluationContext:
    dataset = DatasetRef(
        dataset_id="incident-cases",
        version="1",
        source="fixture",
        schema_id="incident-v1",
        content_hash="sha256:fixture",
        created_at=NOW,
    )
    candidate = CandidateRef(
        candidate_id="triage-agent",
        version="2",
        adapter="fake:agent",
        created_at=NOW,
    )
    return EvaluationContext(dataset=dataset, candidate=candidate, namespace="triage-eval")


def _cases():
    return (
        GenerativeCase(
            case_id="db-down",
            prompt="Database connections fail after deploy",
            expected_label="sev1",
            expected_tool="rollback",
            relevant_retrieval_ids=("runbook-db",),
            supported_claims=("deploy-correlated", "db-unreachable"),
        ),
        GenerativeCase(
            case_id="cache-latency",
            prompt="Cache latency elevated but requests succeed",
            expected_label="sev3",
            expected_tool="inspect-cache",
            relevant_retrieval_ids=("runbook-cache", "dashboard-cache"),
            supported_claims=("cache-latency",),
        ),
    )


class FakeCandidate:
    def invoke(self, case: GenerativeCase) -> GenerativeOutput:
        if case.case_id == "db-down":
            return GenerativeOutput(
                case_id=case.case_id,
                label="sev1",
                structured_valid=True,
                selected_tool="rollback",
                retrieved_ids=("runbook-db",),
                claims=("deploy-correlated", "db-unreachable"),
                latency_ms=100,
                cost_units=2,
            )
        return GenerativeOutput(
            case_id=case.case_id,
            label="sev2",
            structured_valid=False,
            selected_tool="inspect-cache",
            retrieved_ids=("runbook-cache", "irrelevant"),
            claims=("cache-latency", "database-down"),
            latency_ms=300,
            cost_units=3,
        )


def test_fake_candidate_and_deterministic_metrics():
    cases = _cases()
    outputs = run_candidate(FakeCandidate(), cases)
    metrics = {item.name: item for item in evaluate_generative(_context(), cases, outputs)}

    assert metrics["task_accuracy"].value == pytest.approx(0.5)
    assert metrics["structured_output_validity"].value == pytest.approx(0.5)
    assert metrics["tool_selection_accuracy"].value == pytest.approx(1.0)
    assert metrics["retrieval_recall"].value == pytest.approx(0.75)
    assert metrics["retrieval_precision"].value == pytest.approx(0.75)
    assert metrics["unsupported_claim_rate"].value == pytest.approx(0.25)
    assert metrics["mean_latency_ms"].value == pytest.approx(200)
    assert metrics["total_cost_units"].value == pytest.approx(5)
    assert all(item.metadata["evidence_type"] == "deterministic" for item in metrics.values())
    assert metrics["unsupported_claim_rate"].direction == MetricDirection.MINIMIZE


def test_judge_metric_is_explicitly_non_authoritative():
    metric = judge_metrics(
        _context(),
        (
            JudgeResult("db-down", "fake-judge-v1", "config-abc", 4, scale_min=1, scale_max=5),
            JudgeResult("cache-latency", "fake-judge-v1", "config-abc", 3, scale_min=1, scale_max=5),
        ),
    )[0]
    assert metric.name == "judge_score"
    assert metric.value == pytest.approx(0.625)
    assert metric.metadata["evidence_type"] == "judge_model"
    assert metric.metadata["authoritative_ground_truth"] is False
    assert metric.metadata["judge_id"] == "fake-judge-v1"
    assert metric.metadata["judge_config_hash"] == "config-abc"


def test_judge_results_with_different_provenance_cannot_be_mixed():
    with pytest.raises(EvaluationError, match="different judges"):
        judge_metrics(
            _context(),
            (
                JudgeResult("a", "judge-a", "config", 1),
                JudgeResult("b", "judge-b", "config", 1),
            ),
        )


def test_case_output_alignment_is_required():
    cases = _cases()
    outputs = tuple(reversed(run_candidate(FakeCandidate(), cases)))
    with pytest.raises(EvaluationError, match="IDs must align"):
        evaluate_generative(_context(), cases, outputs)
