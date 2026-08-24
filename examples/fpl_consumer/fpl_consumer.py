"""Focused FPL consumer proving the platform contracts without FPL logic in core.

This module is intentionally outside ``ml_ai_platform``.  It owns historical
snapshot interpretation, feature construction, a tiny learned model, and the
forecast target.  The platform owns registration, evaluation, findings, and
promotion evidence.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from ml_ai_platform.contracts import CandidateRef, DatasetRef, EvaluationRun, ExperimentSpec, content_identity
from ml_ai_platform.evaluation import (
    EvaluationContext,
    MetricGate,
    comparison_findings,
    probability_metrics,
    regression_metrics,
    sliced_metrics,
)
from ml_ai_platform.lifecycle import ChampionLifecycle, PromotionPolicy
from ml_ai_platform.registry import FilesystemRegistry

HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "fixture.json"
CREATED = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)
TRAIN_AS_OF = datetime(2026, 5, 20, 0, 0, tzinfo=UTC)
RESOLVED_AS_OF = datetime(2026, 5, 25, 0, 0, tzinfo=UTC)


def load_fixture(path: Path = FIXTURE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature(row: dict, gw: str) -> list[float]:
    value = row[gw]
    return [1.0, float(value["points"]), float(value["ict"]), float(value["minutes"]) / 90.0]


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a small dense system with deterministic partial pivoting."""

    n = len(vector)
    work = [list(row) + [float(vector[index])] for index, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-12:
            raise ValueError("singular linear system")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [value / scale for value in work[column]]
        for row in range(n):
            if row == column:
                continue
            factor = work[row][column]
            work[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(work[row], work[column], strict=True)
            ]
    return [work[row][-1] for row in range(n)]


def fit_ridge(features: Iterable[list[float]], labels: Iterable[float], ridge: float = 1.0) -> list[float]:
    x = list(features)
    y = [float(value) for value in labels]
    if not x or len(x) != len(y):
        raise ValueError("training features and labels must be non-empty and aligned")
    width = len(x[0])
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, label in zip(x, y, strict=True):
        if len(row) != width:
            raise ValueError("inconsistent feature width")
        for left in range(width):
            xty[left] += row[left] * label
            for right in range(width):
                xtx[left][right] += row[left] * row[right]
    for index in range(1, width):
        xtx[index][index] += ridge
    return _solve(xtx, xty)


def predict(weights: list[float], feature: list[float]) -> float:
    return sum(left * right for left, right in zip(weights, feature, strict=True))


def points_probability(points_prediction: float) -> float:
    """Consumer-side mapping for the event: score at least two FPL points."""

    return 1.0 / (1.0 + math.exp(-(points_prediction - 2.0)))


def _evaluation_run(
    registry: FilesystemRegistry,
    *,
    run_id: str,
    experiment_id: str,
    dataset: DatasetRef,
    candidate: CandidateRef,
    truth: list[float],
    predictions: list[float],
    positions: list[str],
) -> EvaluationRun:
    experiment = ExperimentSpec(
        experiment_id=experiment_id,
        version="1",
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        evaluator_ids=("regression", "probability"),
        created_at=CREATED,
        slice_ids=tuple(sorted(set(positions))),
        code_ref="examples/fpl_consumer/fpl_consumer.py",
        metadata={"consumer": "fpl", "forecast_target": "gw38_points"},
    )
    registry.put(experiment)
    context = EvaluationContext(dataset=dataset, candidate=candidate, namespace=run_id)
    metrics = list(regression_metrics(context, truth, predictions))
    metrics.extend(sliced_metrics(regression_metrics, context, truth, predictions, positions))
    probability_truth = [1 if value >= 2 else 0 for value in truth]
    probabilities = [points_probability(value) for value in predictions]
    metrics.extend(probability_metrics(context, probability_truth, probabilities, bins=4))
    run = EvaluationRun(
        run_id=run_id,
        experiment_ref=experiment.ref,
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        started_at=CREATED,
        completed_at=CREATED,
        code_ref="examples/fpl_consumer/fpl_consumer.py",
        config_hash=content_identity({"truth": truth, "predictions": predictions, "positions": positions}),
        metrics=tuple(metrics),
        metadata={"consumer": "fpl", "evaluation_gameweek": 38},
    )
    registry.put(run)
    return run


def run_demo(registry_root: str | Path) -> dict:
    fixture = load_fixture()
    registry = FilesystemRegistry(registry_root)
    players = fixture["players"]
    source = fixture["source"]

    train_dataset = DatasetRef(
        dataset_id="fpl-2025-26-gw37-cutoff",
        version="1",
        source="vaastav/Fantasy-Premier-League",
        schema_id="focused-player-history-v1",
        content_hash=content_identity({"gw36": source["files"]["gw36"], "gw37": source["files"]["gw37"], "players": players}),
        created_at=CREATED,
        as_of=TRAIN_AS_OF,
        metadata={"season": "2025-26", "through_gameweek": 37, "source_files": source["files"]},
    )
    evaluation_dataset = DatasetRef(
        dataset_id="fpl-2025-26-gw38-resolved",
        version="1",
        source="vaastav/Fantasy-Premier-League",
        schema_id="focused-player-history-v1",
        content_hash=content_identity(fixture),
        created_at=CREATED,
        as_of=RESOLVED_AS_OF,
        parents=(train_dataset.ref,),
        metadata={"season": "2025-26", "resolved_gameweek": 38, "source_files": source["files"]},
    )
    registry.put(train_dataset)
    registry.put(evaluation_dataset)

    baseline = CandidateRef(
        candidate_id="fpl-last-gameweek-points",
        version="1",
        adapter="heuristic:last-gameweek-points",
        created_at=CREATED,
        code_ref="examples/fpl_consumer/fpl_consumer.py",
        metadata={"training_as_of": TRAIN_AS_OF.isoformat(), "uses": ["gw37.points"]},
    )
    learned = CandidateRef(
        candidate_id="fpl-ridge-points",
        version="1",
        adapter="linear:ridge",
        created_at=CREATED,
        code_ref="examples/fpl_consumer/fpl_consumer.py",
        metadata={
            "training_dataset": {"id": train_dataset.dataset_id, "version": train_dataset.version},
            "training_pair": "gw36_features_to_gw37_points",
            "ridge": 1.0,
        },
    )
    registry.put(baseline)
    registry.put(learned)

    weights = fit_ridge((_feature(row, "gw36") for row in players), (row["gw37"]["points"] for row in players))
    truth = [float(row["gw38"]["points"]) for row in players]
    baseline_predictions = [float(row["gw37"]["points"]) for row in players]
    learned_predictions = [predict(weights, _feature(row, "gw37")) for row in players]
    positions = [row["position"] for row in players]

    baseline_run = _evaluation_run(
        registry,
        run_id="fpl-gw38-baseline",
        experiment_id="fpl-gw38-baseline",
        dataset=evaluation_dataset,
        candidate=baseline,
        truth=truth,
        predictions=baseline_predictions,
        positions=positions,
    )
    learned_run = _evaluation_run(
        registry,
        run_id="fpl-gw38-ridge",
        experiment_id="fpl-gw38-ridge",
        dataset=evaluation_dataset,
        candidate=learned,
        truth=truth,
        predictions=learned_predictions,
        positions=positions,
    )

    findings = comparison_findings(baseline_run.metrics, learned_run.metrics)
    for finding in findings:
        registry.put(finding)

    lifecycle = ChampionLifecycle(registry)
    initial = lifecycle.decide(
        decision_id="fpl-gw38-baseline-accept",
        candidate_ref=baseline.ref,
        challenger_run_id=baseline_run.run_id,
        policy=PromotionPolicy("fpl-points", "1"),
        channel="fpl-player-points",
        created_at=CREATED,
    )
    challenger_decision = lifecycle.decide(
        decision_id="fpl-gw38-ridge-decision",
        candidate_ref=learned.ref,
        challenger_run_id=learned_run.run_id,
        incumbent_run_id=baseline_run.run_id,
        policy=PromotionPolicy("fpl-points", "2", gates=(MetricGate("mae", max_regression=0.0),)),
        channel="fpl-player-points",
        created_at=CREATED,
    )

    metric = lambda run, name: next(item.value for item in run.metrics if item.name == name and item.slice_id is None)
    return {
        "training_dataset": train_dataset.to_dict(),
        "evaluation_dataset": evaluation_dataset.to_dict(),
        "candidates": [baseline.to_dict(), learned.to_dict()],
        "weights": weights,
        "baseline": {"run_id": baseline_run.run_id, "mae": metric(baseline_run, "mae")},
        "learned": {"run_id": learned_run.run_id, "mae": metric(learned_run, "mae")},
        "findings": [item.to_dict() for item in findings],
        "initial_decision": initial.to_dict(),
        "challenger_decision": challenger_decision.to_dict(),
        "champion": lifecycle.current("fpl-player-points").to_dict(),
        "leakage_guard": {
            "training_as_of": TRAIN_AS_OF.isoformat(),
            "evaluation_resolved_as_of": RESOLVED_AS_OF.isoformat(),
            "training_uses_gameweeks": [36, 37],
            "prediction_features_gameweek": 37,
            "labels_gameweek": 38,
        },
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        print(json.dumps(run_demo(directory), indent=2, sort_keys=True))
