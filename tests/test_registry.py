from datetime import datetime, timezone

import pytest

from ml_ai_platform.contracts import (
    CandidateRef,
    DatasetRef,
    Decision,
    EvaluationRun,
    ExperimentSpec,
    Finding,
    MetricResult,
    PromotionDecision,
    RecordRef,
)
from ml_ai_platform.registry import (
    FilesystemRegistry,
    RecordAlreadyExists,
    RecordNotFound,
    RegistryError,
)


NOW = datetime(2026, 8, 24, 16, 0, tzinfo=timezone.utc)


def build_records():
    dataset = DatasetRef(
        dataset_id="dataset-a",
        version="1",
        source="fixture",
        schema_id="rows/v1",
        content_hash="sha256:data",
        created_at=NOW,
    )
    candidate = CandidateRef(
        candidate_id="candidate-a",
        version="2",
        adapter="python-callable/v1",
        created_at=NOW,
        code_ref="git:def456",
        config_hash="sha256:config",
    )
    experiment = ExperimentSpec(
        experiment_id="experiment-a",
        version="3",
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        evaluator_ids=("regression/v1",),
        created_at=NOW,
        code_ref="git:def456",
        config_hash="sha256:experiment",
    )
    finding = Finding(
        finding_id="finding-a",
        kind="threshold-violation",
        severity="warning",
        message="Threshold failed.",
    )
    run = EvaluationRun(
        run_id="run-a",
        experiment_ref=experiment.ref,
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        started_at=NOW,
        completed_at=NOW,
        code_ref="git:def456",
        config_hash="sha256:experiment",
        metrics=(MetricResult(metric_id="mae", name="mae", value=4.2),),
        findings=(finding,),
    )
    decision = PromotionDecision(
        decision_id="decision-a",
        candidate_ref=candidate.ref,
        incumbent_ref=RecordRef("candidate-a", "1"),
        evaluation_run_id=run.run_id,
        policy_version="policy/v1",
        decision=Decision.REJECT,
        created_at=NOW,
        reasons=("threshold failed",),
    )
    return dataset, candidate, experiment, run, finding, decision


def test_registry_round_trips_all_top_level_records(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    dataset, candidate, experiment, run, finding, decision = build_records()

    for record in (dataset, candidate, experiment, run, finding, decision):
        relative = registry.put(record).relative_to(tmp_path)
        assert registry.get(relative) == record

    assert registry.get_dataset("dataset-a", "1") == dataset
    assert registry.get_candidate("candidate-a", "2") == candidate
    assert registry.get_experiment("experiment-a", "3") == experiment
    assert registry.get_evaluation_run("run-a") == run
    assert registry.get_finding("finding-a") == finding
    assert registry.get_promotion_decision("decision-a") == decision


def test_registry_refuses_to_silently_overwrite_existing_key(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    dataset, *_ = build_records()
    registry.put(dataset)

    changed_same_identity = DatasetRef(
        dataset_id=dataset.dataset_id,
        version=dataset.version,
        source="different-source",
        schema_id=dataset.schema_id,
        content_hash="sha256:changed",
        created_at=NOW,
    )

    with pytest.raises(RecordAlreadyExists):
        registry.put(changed_same_identity)

    assert registry.get_dataset(dataset.dataset_id, dataset.version) == dataset


def test_registry_paths_are_deterministic_and_sorted(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    for version in ("3", "1", "2"):
        registry.put(
            DatasetRef(
                dataset_id="dataset-a",
                version=version,
                source="fixture",
                schema_id="rows/v1",
                content_hash=f"sha256:{version}",
                created_at=NOW,
            )
        )

    paths = [str(path) for path in registry.iter_paths("datasets")]
    assert paths == [
        "datasets/dataset-a/1.json",
        "datasets/dataset-a/2.json",
        "datasets/dataset-a/3.json",
    ]


def test_registry_blocks_path_traversal_and_missing_records(tmp_path):
    registry = FilesystemRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.get("../outside.json")

    with pytest.raises(RecordNotFound):
        registry.get_dataset("missing", "1")


def test_registry_rejects_unsafe_identifiers(tmp_path):
    registry = FilesystemRegistry(tmp_path)
    record = DatasetRef(
        dataset_id="../escape",
        version="1",
        source="fixture",
        schema_id="rows/v1",
        content_hash="sha256:data",
        created_at=NOW,
    )

    with pytest.raises(RegistryError, match="unsafe registry key"):
        registry.put(record)
