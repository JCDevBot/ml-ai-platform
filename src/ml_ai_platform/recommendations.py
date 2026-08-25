"""Deterministic next-experiment recommendations derived from measured findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Mapping, Sequence

from .contracts import Finding


JsonScalar = None | bool | int | float | str


class RecommendationError(ValueError):
    """Raised when a recommendation/search specification is invalid."""


@dataclass(frozen=True, slots=True)
class ExperimentRecommendation:
    recommendation_id: str
    rule_id: str
    rule_version: str
    evaluation_run_id: str
    finding_ids: tuple[str, ...]
    action: str
    rationale: str
    parameters: Mapping[str, JsonScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "recommendation_id",
            "rule_id",
            "rule_version",
            "evaluation_run_id",
            "action",
            "rationale",
        ):
            if not str(getattr(self, name)).strip():
                raise RecommendationError(f"{name} is required")
        if not self.finding_ids:
            raise RecommendationError("finding_ids must reference exact evidence")


@dataclass(frozen=True, slots=True)
class BoundedSearchSpace:
    """Explicit finite search space with deterministic trial enumeration."""

    choices: Mapping[str, tuple[JsonScalar, ...]]
    max_trials: int

    def __post_init__(self) -> None:
        if self.max_trials <= 0:
            raise RecommendationError("max_trials must be positive")
        if not self.choices:
            raise RecommendationError("choices must not be empty")
        for name, values in self.choices.items():
            if not name.strip() or not values:
                raise RecommendationError("each search parameter requires a name and choices")

    def trials(self) -> tuple[dict[str, JsonScalar], ...]:
        keys = tuple(sorted(self.choices))
        combinations = product(*(self.choices[key] for key in keys))
        return tuple(
            dict(zip(keys, values, strict=True))
            for _, values in zip(range(self.max_trials), combinations, strict=False)
        )


_RULE_VERSION = "1"

_RULES: dict[str, tuple[str, str]] = {
    "regression": (
        "investigate_regression",
        "Run a bounded challenger change targeted at the regressed metric before reconsidering promotion.",
    ),
    "protected_slice_regression": (
        "improve_protected_slice",
        "Target the protected slice regression while preserving headline performance.",
    ),
    "calibration_failure": (
        "improve_calibration",
        "Evaluate a bounded calibration change using the same probability evidence and gates.",
    ),
    "threshold_violation": (
        "improve_threshold_metric",
        "Change the candidate/config to satisfy the existing policy threshold; do not weaken policy automatically.",
    ),
}


def recommend_experiments(
    *,
    evaluation_run_id: str,
    findings: Sequence[Finding],
) -> tuple[ExperimentRecommendation, ...]:
    """Map authoritative deterministic findings to stable next-experiment recommendations."""

    if not evaluation_run_id.strip():
        raise RecommendationError("evaluation_run_id is required")

    recommendations: list[ExperimentRecommendation] = []
    for finding in sorted(findings, key=lambda item: item.finding_id):
        rule = _RULES.get(finding.kind)
        if rule is None:
            continue
        action, rationale = rule
        parameters: dict[str, JsonScalar] = {}
        for key in ("metric_name", "slice_id", "max_regression", "min_value", "max_value"):
            value = finding.evidence.get(key)
            if value is None or isinstance(value, (bool, int, float, str)):
                parameters[key] = value

        recommendations.append(
            ExperimentRecommendation(
                recommendation_id=f"recommend:{evaluation_run_id}:{finding.finding_id}:{action}",
                rule_id=f"finding-kind:{finding.kind}",
                rule_version=_RULE_VERSION,
                evaluation_run_id=evaluation_run_id,
                finding_ids=(finding.finding_id,),
                action=action,
                rationale=rationale,
                parameters=parameters,
            )
        )
    return tuple(recommendations)
