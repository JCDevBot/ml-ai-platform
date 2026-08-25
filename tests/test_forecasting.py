from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ml_ai_platform.contracts import CandidateRef, DatasetRef
from ml_ai_platform.evaluation import EvaluationContext
from ml_ai_platform.forecasting import (
    FakeForecastAdapter,
    ForecastError,
    ForecastObservation,
    ForecastResolution,
    evaluate_binary_forecasts,
)


T0 = datetime(2026, 8, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 8, 2, tzinfo=timezone.utc)


def _context(candidate_id: str) -> EvaluationContext:
    dataset = DatasetRef(
        dataset_id="forecast-evidence",
        version="1",
        source="synthetic",
        schema_id="binary-forecast-v1",
        content_hash="abc123",
        created_at=T0,
    )
    candidate = CandidateRef(
        candidate_id=candidate_id,
        version="1",
        adapter="forecast-observation",
        created_at=T0,
    )
    return EvaluationContext(dataset=dataset, candidate=candidate)


def _resolutions() -> tuple[ForecastResolution, ...]:
    return (
        ForecastResolution(target_id="q1", outcome=1, resolved_at=T1),
        ForecastResolution(target_id="q2", outcome=0, resolved_at=T1),
    )


def test_fake_external_consensus_reuses_probability_metrics() -> None:
    adapter = FakeForecastAdapter(
        rows=(
            ForecastObservation(source_id="external-consensus", target_id="q1", probability=0.8, observed_at=T0),
            ForecastObservation(source_id="external-consensus", target_id="q2", probability=0.2, observed_at=T0),
        )
    )

    metrics = evaluate_binary_forecasts(_context("external-consensus"), adapter.observations(), _resolutions())
    by_name = {metric.name: metric.value for metric in metrics}

    assert by_name["brier_score"] == pytest.approx(0.04)
    assert set(by_name) == {"brier_score", "log_loss", "calibration_error"}


def test_external_consensus_can_be_compared_with_internal_baseline() -> None:
    external = FakeForecastAdapter(
        rows=(
            ForecastObservation("external", "q1", 0.8, T0),
            ForecastObservation("external", "q2", 0.2, T0),
        )
    )
    baseline = FakeForecastAdapter(
        rows=(
            ForecastObservation("internal-baseline", "q1", 0.6, T0),
            ForecastObservation("internal-baseline", "q2", 0.4, T0),
        )
    )

    external_metrics = {m.name: m.value for m in evaluate_binary_forecasts(_context("external"), external.observations(), _resolutions())}
    baseline_metrics = {m.name: m.value for m in evaluate_binary_forecasts(_context("internal"), baseline.observations(), _resolutions())}

    assert external_metrics["brier_score"] < baseline_metrics["brier_score"]


def test_forecast_observation_requires_timezone_and_probability_bounds() -> None:
    with pytest.raises(ForecastError, match="timezone-aware"):
        ForecastObservation("source", "q1", 0.5, datetime(2026, 8, 1))
    with pytest.raises(ForecastError, match="between 0 and 1"):
        ForecastObservation("source", "q1", 1.1, T0)


def test_post_resolution_forecast_is_rejected() -> None:
    observation = ForecastObservation("source", "q1", 0.9, datetime(2026, 8, 3, tzinfo=timezone.utc))

    with pytest.raises(ForecastError, match="after resolution"):
        evaluate_binary_forecasts(
            _context("late-source"),
            [observation],
            [ForecastResolution("q1", 1, T1)],
        )


def test_duplicate_target_observations_are_rejected() -> None:
    rows = (
        ForecastObservation("source-a", "q1", 0.7, T0),
        ForecastObservation("source-b", "q1", 0.8, T0),
    )

    with pytest.raises(ForecastError, match="one normalized observation per target"):
        evaluate_binary_forecasts(_context("duplicate"), rows, [ForecastResolution("q1", 1, T1)])


def test_contracts_expose_no_trading_or_credential_fields() -> None:
    observation_fields = ForecastObservation.__dataclass_fields__
    forbidden = {"order", "wallet", "trade", "token", "api_key", "payment", "account"}

    assert forbidden.isdisjoint(observation_fields)
