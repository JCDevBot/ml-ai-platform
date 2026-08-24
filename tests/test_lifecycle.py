from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ml_ai_platform.contracts import (
    CandidateRef,
    DatasetRef,
    Decision,
    EvaluationRun,
    ExperimentSpec,
    MetricDirection,
    MetricResult,
    RecordRef,
)
from ml_ai_platform.evaluation import MetricGate
from ml_ai_platform.lifecycle import ChampionLifecycle, LifecycleError, PromotionPolicy
from ml_ai_platform.registry import FilesystemRegistry, RecordAlreadyExists


NOW = datetime(2026, 8, 24, 18, 0, tzinfo=UTC)


def _metric(candidate: str, name: str, value: float, *, slice_id: str | None = None):
    return MetricResult(
        metric_id=f"{candidate}:{name}:{slice_id or 'all'}",
        name=name,
        value=value,
        direction=MetricDirection.MINIMIZE,
        slice_id=slice_id,
    )


def _seed(registry: FilesystemRegistry):
    dataset = DatasetRef(
        dataset_id="dataset",
        version="1",
        source="fixture",
        schema_id="v1",
        content_hash="sha256:fixture",
        created_at=NOW,
    )
    baseline = CandidateRef(candidate_id="baseline", version="1", adapter="fixture", created_at=NOW)
    challenger = CandidateRef(candidate_id="challenger", version="1", adapter="fixture", created_at=NOW)
    third = CandidateRef(candidate_id="third", version="1", adapter="fixture", created_at=NOW)
    for record in (dataset, baseline, challenger, third):
        registry.put(record)

    runs = {
        "baseline-run": (baseline, (_metric("baseline", "mae", 2.0), _metric("baseline", "mae", 2.0, slice_id="protected"))),
        "challenger-run": (challenger, (_metric("challenger", "mae", 1.5), _metric("challenger", "mae", 3.0, slice_id="protected"))),
        "good-run": (third, (_metric("third", "mae", 1.0), _metric("third", "mae", 1.5, slice_id="protected"))),
    }
    for index, (run_id, (candidate, metrics)) in enumerate(runs.items(), start=1):
        experiment = ExperimentSpec(
            experiment_id=f"exp-{index}",
            version="1",
            dataset_refs=(dataset.ref,),
            candidate_refs=(candidate.ref,),
            evaluator_ids=("regression",),
            created_at=NOW,
        )
        registry.put(experiment)
        registry.put(
            EvaluationRun(
                run_id=run_id,
                experiment_ref=experiment.ref,
                dataset_refs=(dataset.ref,),
                candidate_refs=(candidate.ref,),
                started_at=NOW,
                completed_at=NOW,
                code_ref=f"code-{index}",
                config_hash=f"config-{index}",
                metrics=metrics,
            )
        )
    return baseline, challenger, third


def test_accept_then_protected_slice_reject(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, challenger, _ = _seed(registry)
    lifecycle = ChampionLifecycle(registry)

    initial = lifecycle.decide(
        decision_id="decision-initial",
        candidate_ref=baseline.ref,
        challenger_run_id="baseline-run",
        policy=PromotionPolicy("standard", "1"),
        created_at=NOW,
    )
    assert initial.decision == Decision.ACCEPT
    assert lifecycle.current().candidate_ref == baseline.ref

    policy = PromotionPolicy(
        "standard",
        "2",
        gates=(MetricGate("mae", slice_id="protected", max_regression=0.25, protected_slice=True),),
    )
    rejected = lifecycle.decide(
        decision_id="decision-reject",
        candidate_ref=challenger.ref,
        challenger_run_id="challenger-run",
        incumbent_run_id="baseline-run",
        policy=policy,
        created_at=NOW,
    )
    assert rejected.decision == Decision.REJECT
    assert any("adverse delta" in reason for reason in rejected.reasons)
    assert lifecycle.current().candidate_ref == baseline.ref
    history = lifecycle.history()
    assert [item.decision_id for item in history] == ["decision-initial", "decision-reject"]


def test_human_review_does_not_move_alias(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, challenger, _ = _seed(registry)
    lifecycle = ChampionLifecycle(registry)
    lifecycle.decide(
        decision_id="accepted",
        candidate_ref=baseline.ref,
        challenger_run_id="baseline-run",
        policy=PromotionPolicy("standard", "1"),
        created_at=NOW,
    )
    review = lifecycle.decide(
        decision_id="needs-review",
        candidate_ref=challenger.ref,
        challenger_run_id="challenger-run",
        incumbent_run_id="baseline-run",
        policy=PromotionPolicy("human", "1", require_human_review=True),
        created_at=NOW,
    )
    assert review.decision == Decision.REVIEW
    assert review.evaluation_run_id == "challenger-run"
    assert review.policy_version == "human@1"
    assert lifecycle.current().candidate_ref == baseline.ref


def test_missing_incumbent_evidence_cannot_promote(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, challenger, _ = _seed(registry)
    lifecycle = ChampionLifecycle(registry)
    lifecycle.decide(
        decision_id="accepted",
        candidate_ref=baseline.ref,
        challenger_run_id="baseline-run",
        policy=PromotionPolicy("standard", "1"),
        created_at=NOW,
    )
    decision = lifecycle.decide(
        decision_id="missing-evidence",
        candidate_ref=challenger.ref,
        challenger_run_id="challenger-run",
        policy=PromotionPolicy("standard", "2"),
        created_at=NOW,
    )
    assert decision.decision == Decision.REVIEW
    assert "incumbent evaluation evidence is required" in decision.reasons
    assert lifecycle.current().candidate_ref == baseline.ref


def test_rollback_appends_history_and_restores_prior_champion(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, _, third = _seed(registry)
    lifecycle = ChampionLifecycle(registry)
    lifecycle.decide(
        decision_id="baseline-accepted",
        candidate_ref=baseline.ref,
        challenger_run_id="baseline-run",
        policy=PromotionPolicy("standard", "1"),
        created_at=NOW,
    )
    lifecycle.decide(
        decision_id="third-accepted",
        candidate_ref=third.ref,
        challenger_run_id="good-run",
        incumbent_run_id="baseline-run",
        policy=PromotionPolicy(
            "standard",
            "2",
            gates=(MetricGate("mae", max_regression=0.0),),
        ),
        created_at=NOW,
    )
    assert lifecycle.current().candidate_ref == third.ref

    rolled_back = lifecycle.rollback(
        decision_id="rollback-baseline",
        target_ref=baseline.ref,
        evaluation_run_id="baseline-run",
        created_at=NOW,
    )
    assert rolled_back.decision == Decision.ACCEPT
    assert rolled_back.metadata["action"] == "rollback"
    assert lifecycle.current().candidate_ref == baseline.ref
    assert [item.decision_id for item in lifecycle.history()] == [
        "baseline-accepted",
        "rollback-baseline",
        "third-accepted",
    ]


def test_rollback_requires_previously_accepted_target(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, challenger, _ = _seed(registry)
    lifecycle = ChampionLifecycle(registry)
    lifecycle.decide(
        decision_id="accepted",
        candidate_ref=baseline.ref,
        challenger_run_id="baseline-run",
        policy=PromotionPolicy("standard", "1"),
        created_at=NOW,
    )
    with pytest.raises(LifecycleError, match="not previously accepted"):
        lifecycle.rollback(
            decision_id="bad-rollback",
            target_ref=challenger.ref,
            evaluation_run_id="challenger-run",
            created_at=NOW,
        )


def test_policy_versions_are_immutable(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    lifecycle = ChampionLifecycle(registry)
    policy = PromotionPolicy("standard", "1", gates=(MetricGate("mae", max_value=2.0),))
    lifecycle.save_policy(policy)
    assert lifecycle.load_policy("standard", "1") == policy
    assert lifecycle.save_policy(policy).exists()
    with pytest.raises(RecordAlreadyExists):
        lifecycle.save_policy(PromotionPolicy("standard", "1", gates=(MetricGate("mae", max_value=3.0),)))


def test_challenger_run_must_reference_candidate(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    baseline, challenger, _ = _seed(registry)
    lifecycle = ChampionLifecycle(registry)
    with pytest.raises(LifecycleError, match="does not reference candidate"):
        lifecycle.decide(
            decision_id="mismatch",
            candidate_ref=challenger.ref,
            challenger_run_id="baseline-run",
            policy=PromotionPolicy("standard", "1"),
            created_at=NOW,
        )
