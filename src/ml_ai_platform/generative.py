"""Provider-neutral deterministic evaluation for LLM, RAG, and agent candidates.

Consumers/adapters execute candidates.  This module evaluates recorded outcomes
without importing any model provider.  Optional judge-model evidence is marked
explicitly and is never represented as deterministic ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from .contracts import JsonValue, MetricDirection, MetricResult
from .evaluation import EvaluationContext, EvaluationError


@dataclass(frozen=True, slots=True)
class GenerativeCase:
    """One labeled evaluation case independent of a model provider."""

    case_id: str
    prompt: str
    expected_label: str | None = None
    expected_tool: str | None = None
    relevant_retrieval_ids: tuple[str, ...] = ()
    supported_claims: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise EvaluationError("case_id must be non-empty")
        if not self.prompt.strip():
            raise EvaluationError("prompt must be non-empty")


@dataclass(frozen=True, slots=True)
class GenerativeOutput:
    """Recorded candidate outcome consumed by deterministic evaluators."""

    case_id: str
    label: str | None = None
    structured_valid: bool = True
    selected_tool: str | None = None
    retrieved_ids: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    latency_ms: float | None = None
    cost_units: float | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise EvaluationError("case_id must be non-empty")
        for name in ("latency_ms", "cost_units"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise EvaluationError(f"{name} cannot be negative")


class GenerativeCandidate(Protocol):
    """Minimal adapter contract; provider implementations can live in extras."""

    def invoke(self, case: GenerativeCase) -> GenerativeOutput: ...


@dataclass(frozen=True, slots=True)
class JudgeResult:
    """Optional subjective/judge-model evidence with mandatory provenance."""

    case_id: str
    judge_id: str
    config_hash: str
    score: float
    scale_min: float = 0.0
    scale_max: float = 1.0
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.judge_id.strip() or not self.config_hash.strip():
            raise EvaluationError("judge case_id, judge_id, and config_hash must be non-empty")
        if self.scale_max <= self.scale_min:
            raise EvaluationError("judge scale_max must exceed scale_min")
        if not self.scale_min <= self.score <= self.scale_max:
            raise EvaluationError("judge score must be within its declared scale")


def run_candidate(candidate: GenerativeCandidate, cases: Sequence[GenerativeCase]) -> tuple[GenerativeOutput, ...]:
    """Execute a provider-neutral candidate adapter and enforce case alignment."""

    outputs = tuple(candidate.invoke(case) for case in cases)
    expected = [case.case_id for case in cases]
    actual = [output.case_id for output in outputs]
    if actual != expected:
        raise EvaluationError("candidate outputs must preserve evaluation case order and IDs")
    return outputs


def _metric(
    context: EvaluationContext,
    name: str,
    value: float,
    direction: MetricDirection,
    *,
    metadata: Mapping[str, JsonValue] | None = None,
) -> MetricResult:
    return MetricResult(
        metric_id=f"{context.namespace}:{context.candidate.candidate_id}:{context.candidate.version}:{name}",
        name=name,
        value=float(value),
        direction=direction,
        metadata={
            "dataset_id": context.dataset.dataset_id,
            "dataset_version": context.dataset.version,
            "candidate_id": context.candidate.candidate_id,
            "candidate_version": context.candidate.version,
            "evidence_type": "deterministic",
            **dict(metadata or {}),
        },
    )


def evaluate_generative(
    context: EvaluationContext,
    cases: Sequence[GenerativeCase],
    outputs: Sequence[GenerativeOutput],
) -> tuple[MetricResult, ...]:
    """Calculate deterministic labeled, tool, retrieval, claim, latency, and cost metrics."""

    if not cases or len(cases) != len(outputs):
        raise EvaluationError("generative evaluation requires aligned non-empty cases and outputs")
    if [case.case_id for case in cases] != [output.case_id for output in outputs]:
        raise EvaluationError("generative case/output IDs must align in order")

    metrics: list[MetricResult] = []
    labeled = [(case, output) for case, output in zip(cases, outputs, strict=True) if case.expected_label is not None]
    if labeled:
        accuracy = sum(output.label == case.expected_label for case, output in labeled) / len(labeled)
        metrics.append(_metric(context, "task_accuracy", accuracy, MetricDirection.MAXIMIZE, metadata={"cases": len(labeled)}))

    structured = sum(output.structured_valid for output in outputs) / len(outputs)
    metrics.append(
        _metric(
            context,
            "structured_output_validity",
            structured,
            MetricDirection.MAXIMIZE,
            metadata={"cases": len(outputs)},
        )
    )

    tool_cases = [(case, output) for case, output in zip(cases, outputs, strict=True) if case.expected_tool is not None]
    if tool_cases:
        tool_accuracy = sum(output.selected_tool == case.expected_tool for case, output in tool_cases) / len(tool_cases)
        metrics.append(
            _metric(context, "tool_selection_accuracy", tool_accuracy, MetricDirection.MAXIMIZE, metadata={"cases": len(tool_cases)})
        )

    retrieval_cases = [
        (case, output)
        for case, output in zip(cases, outputs, strict=True)
        if case.relevant_retrieval_ids
    ]
    if retrieval_cases:
        recalls = []
        precisions = []
        for case, output in retrieval_cases:
            relevant = set(case.relevant_retrieval_ids)
            retrieved = set(output.retrieved_ids)
            overlap = len(relevant & retrieved)
            recalls.append(overlap / len(relevant))
            precisions.append(overlap / len(retrieved) if retrieved else 0.0)
        metrics.append(_metric(context, "retrieval_recall", sum(recalls) / len(recalls), MetricDirection.MAXIMIZE))
        metrics.append(_metric(context, "retrieval_precision", sum(precisions) / len(precisions), MetricDirection.MAXIMIZE))

    claim_cases = [(case, output) for case, output in zip(cases, outputs, strict=True) if output.claims]
    if claim_cases:
        claim_count = 0
        unsupported = 0
        for case, output in claim_cases:
            supported = set(case.supported_claims)
            claim_count += len(output.claims)
            unsupported += sum(claim not in supported for claim in output.claims)
        metrics.append(
            _metric(
                context,
                "unsupported_claim_rate",
                unsupported / claim_count,
                MetricDirection.MINIMIZE,
                metadata={"claims": claim_count, "unsupported_claims": unsupported},
            )
        )

    latencies = [float(output.latency_ms) for output in outputs if output.latency_ms is not None]
    if latencies:
        metrics.append(_metric(context, "mean_latency_ms", sum(latencies) / len(latencies), MetricDirection.MINIMIZE))

    costs = [float(output.cost_units) for output in outputs if output.cost_units is not None]
    if costs:
        metrics.append(_metric(context, "total_cost_units", sum(costs), MetricDirection.MINIMIZE))

    return tuple(metrics)


def judge_metrics(context: EvaluationContext, results: Sequence[JudgeResult]) -> tuple[MetricResult, ...]:
    """Aggregate subjective judge evidence while preserving judge provenance."""

    if not results:
        return ()
    identities = {(item.judge_id, item.config_hash, item.scale_min, item.scale_max) for item in results}
    if len(identities) != 1:
        raise EvaluationError("judge metrics cannot aggregate different judges/configurations/scales")
    judge_id, config_hash, scale_min, scale_max = next(iter(identities))
    normalized = [(item.score - scale_min) / (scale_max - scale_min) for item in results]
    return (
        MetricResult(
            metric_id=f"{context.namespace}:{context.candidate.candidate_id}:{context.candidate.version}:judge_score",
            name="judge_score",
            value=sum(normalized) / len(normalized),
            direction=MetricDirection.MAXIMIZE,
            metadata={
                "dataset_id": context.dataset.dataset_id,
                "dataset_version": context.dataset.version,
                "candidate_id": context.candidate.candidate_id,
                "candidate_version": context.candidate.version,
                "evidence_type": "judge_model",
                "authoritative_ground_truth": False,
                "judge_id": judge_id,
                "judge_config_hash": config_hash,
                "source_scale_min": scale_min,
                "source_scale_max": scale_max,
                "cases": len(results),
            },
        ),
    )
