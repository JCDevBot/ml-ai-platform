"""Provider-neutral read-only forecast observations and evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from .evaluation import EvaluationContext, probability_metrics
from .contracts import MetricResult


class ForecastError(ValueError):
    """Raised when normalized forecast evidence is invalid."""


@dataclass(frozen=True, slots=True)
class ForecastObservation:
    source_id: str
    target_id: str
    probability: float
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ForecastError("source_id and target_id are required")
        if not 0.0 <= float(self.probability) <= 1.0:
            raise ForecastError("probability must be between 0 and 1")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ForecastError("observed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ForecastResolution:
    target_id: str
    outcome: int
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ForecastError("target_id is required")
        if self.outcome not in (0, 1):
            raise ForecastError("outcome must be 0 or 1")
        if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() is None:
            raise ForecastError("resolved_at must be timezone-aware")


class ReadOnlyForecastAdapter(Protocol):
    def observations(self) -> Sequence[ForecastObservation]: ...


@dataclass(frozen=True, slots=True)
class FakeForecastAdapter:
    rows: tuple[ForecastObservation, ...]

    def observations(self) -> tuple[ForecastObservation, ...]:
        return self.rows


def evaluate_binary_forecasts(
    context: EvaluationContext,
    observations: Sequence[ForecastObservation],
    resolutions: Sequence[ForecastResolution],
) -> tuple[MetricResult, ...]:
    """Evaluate normalized probability forecasts with existing probability metrics."""

    if not observations:
        raise ForecastError("at least one observation is required")
    if not resolutions:
        raise ForecastError("at least one resolution is required")

    by_target = {item.target_id: item for item in resolutions}
    if len(by_target) != len(resolutions):
        raise ForecastError("resolution target_id values must be unique")

    ordered = sorted(observations, key=lambda item: (item.target_id, item.observed_at, item.source_id))
    if len({item.target_id for item in ordered}) != len(ordered):
        raise ForecastError("one normalized observation per target is required for evaluation")

    truth: list[int] = []
    probabilities: list[float] = []
    for observation in ordered:
        resolution = by_target.get(observation.target_id)
        if resolution is None:
            raise ForecastError(f"missing resolution for target {observation.target_id}")
        if observation.observed_at > resolution.resolved_at:
            raise ForecastError(f"forecast for {observation.target_id} was observed after resolution")
        truth.append(resolution.outcome)
        probabilities.append(float(observation.probability))

    return probability_metrics(context, truth, probabilities)
