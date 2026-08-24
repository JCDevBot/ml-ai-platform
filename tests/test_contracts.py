from datetime import datetime, timedelta, timezone

import pytest

from ml_ai_platform.contracts import (
    CandidateRef,
    ContractError,
    DatasetRef,
    Decision,
    EvaluationRun,
    ExperimentSpec,
    Finding,
    MetricDirection,
    MetricResult,
    PromotionDecision,
    RecordRef,
    canonical_json,
    content_identity,
    contract_from_json,
)


NOW = datetime(2026, 8, 24, 16, 0, tzinfo=timezone.utc)


def dataset() -> DatasetRef:
    return DatasetRef(
        dataset_id="fpl-history",
        version="2026-gw10",
        source="consumer:fpl",
        schema_id="player-week/v1",
        content_hash="sha256:data",
        created_at=NOW,
        as_of=NOW - timedelta(hours=1),
        feature_version="features-v3",
        parents=(RecordRef("raw-fpl", "2026-gw10"),),
        metadata={"rows": 1234},
    )


def candidate() -> CandidateRef:
    return CandidateRef(
        candidate_id="player-points",
        version="12",
        adapter="python-callable/v1",
        created_at=NOW,
        artifact_uri="file:///models/player-points-v12.pkl",
        code_ref="git:abc123",
        config_hash="sha256:config",
        metadata={"family": "gradient-boosted"},
    )


def experiment() -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id="player-points-eval",
        version="4",
        dataset_refs=(dataset().ref,),
        candidate_refs=(candidate().ref,),
        evaluator_ids=("regression/v1",),
        created_at=NOW,
        baseline_candidate_refs=(RecordRef("rolling-average", "3"),),
        slice_ids=("position", "home-away"),
        policy_version="promotion/v1",
        code_ref="git:abc123",
        config_hash="sha256:experiment",
    )


def evaluation_run() -> EvaluationRun:
    metric = MetricResult(
        metric_id="mae:overall",
        name="mae",
        value=3.71,
        direction=MetricDirection.MINIMIZE,
    )
    finding = Finding(
        finding_id="finding-1",
        kind="improvement",
        severity="info",
        message="Candidate improved MAE versus baseline.",
        metric_ids=(metric.metric_id,),
        evidence={"delta_pct": 6.2},
    )
    return EvaluationRun(
        run_id="run-2026-08-24-001",
        experiment_ref=experiment().ref,
        dataset_refs=(dataset().ref,),
        candidate_refs=(candidate().ref,),
        started_at=NOW,
        completed_at=NOW + timedelta(minutes=3),
        code_ref="git:abc123",
        config_hash="sha256:experiment",
        metrics=(metric,),
        findings=(finding,),
        artifact_refs=("file:///reports/run-1.json",),
    )


@pytest.mark.parametrize(
    "record",
    [
        dataset(),
        candidate(),
        experiment(),
        evaluation_run(),
        Finding(
            finding_id="finding-standalone",
            kind="warning",
            severity="warning",
            message="Calibration regressed.",
        ),
        PromotionDecision(
            decision_id="decision-1",
            candidate_ref=candidate().ref,
            incumbent_ref=RecordRef("player-points", "11"),
            evaluation_run_id="run-2026-08-24-001",
            policy_version="promotion/v1",
            decision=Decision.REJECT,
            created_at=NOW,
            reasons=("calibration gate failed",),
        ),
    ],
)
def test_top_level_contracts_round_trip_deterministically(record):
    payload = record.to_json()
    restored = contract_from_json(payload)
    assert restored == record
    assert restored.to_json() == payload


def test_canonical_identity_ignores_mapping_insertion_order():
    first = {"b": 2, "a": 1}
    second = {"a": 1, "b": 2}
    assert canonical_json(first) == canonical_json(second)
    assert content_identity(first) == content_identity(second)


def test_dataset_requires_temporal_timestamps_to_be_timezone_aware():
    with pytest.raises(ContractError, match="created_at must be timezone-aware"):
        DatasetRef(
            dataset_id="data",
            version="1",
            source="test",
            schema_id="schema/v1",
            content_hash="sha256:x",
            created_at=datetime(2026, 8, 24, 10, 0),
        )


def test_experiment_requires_dataset_candidate_and_evaluator():
    with pytest.raises(ContractError, match="dataset_refs"):
        ExperimentSpec(
            experiment_id="empty",
            version="1",
            dataset_refs=(),
            candidate_refs=(candidate().ref,),
            evaluator_ids=("regression/v1",),
            created_at=NOW,
        )


def test_evaluation_run_rejects_inverted_time_range():
    with pytest.raises(ContractError, match="completed_at cannot precede"):
        EvaluationRun(
            run_id="bad-run",
            experiment_ref=experiment().ref,
            dataset_refs=(dataset().ref,),
            candidate_refs=(candidate().ref,),
            started_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
            code_ref="git:abc123",
            config_hash="sha256:config",
        )


def test_candidate_adapter_is_generic_and_provider_metadata_is_optional():
    baseline = CandidateRef(
        candidate_id="rolling-average",
        version="1",
        adapter="deterministic-baseline/v1",
        created_at=NOW,
    )
    llm_pipeline = CandidateRef(
        candidate_id="incident-triage",
        version="prompt-8",
        adapter="llm-pipeline/v1",
        created_at=NOW,
        metadata={"provider": "example-only"},
    )
    assert baseline.adapter != llm_pipeline.adapter
    assert "provider" not in baseline.to_dict()["metadata"]
