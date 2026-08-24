"""Provider-free incident-triage comparison using the platform generative layer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ml_ai_platform.contracts import CandidateRef, DatasetRef, EvaluationRun, ExperimentSpec, content_identity
from ml_ai_platform.evaluation import EvaluationContext, MetricGate, comparison_findings
from ml_ai_platform.generative import GenerativeCase, GenerativeOutput, JudgeResult, evaluate_generative, judge_metrics
from ml_ai_platform.lifecycle import ChampionLifecycle, PromotionPolicy
from ml_ai_platform.registry import FilesystemRegistry

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture.json"
CREATED = datetime(2026, 8, 24, 19, 0, tzinfo=UTC)


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _case(value: dict) -> GenerativeCase:
    return GenerativeCase(
        case_id=value["case_id"],
        prompt=value["prompt"],
        expected_label=value["expected_label"],
        expected_tool=value["expected_tool"],
        relevant_retrieval_ids=tuple(value["relevant_retrieval_ids"]),
        supported_claims=tuple(value["supported_claims"]),
    )


def _output(value: dict) -> GenerativeOutput:
    return GenerativeOutput(
        case_id=value["case_id"],
        label=value.get("label"),
        structured_valid=value["structured_valid"],
        selected_tool=value.get("selected_tool"),
        retrieved_ids=tuple(value.get("retrieved_ids", ())),
        claims=tuple(value.get("claims", ())),
        latency_ms=value.get("latency_ms"),
        cost_units=value.get("cost_units"),
    )


def _run(
    registry: FilesystemRegistry,
    dataset: DatasetRef,
    candidate: CandidateRef,
    cases: tuple[GenerativeCase, ...],
    outputs: tuple[GenerativeOutput, ...],
    judge_scores: list[float],
    judge: dict,
    run_id: str,
) -> EvaluationRun:
    experiment = ExperimentSpec(
        experiment_id=run_id,
        version="1",
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        evaluator_ids=("generative-deterministic", "judge-model"),
        created_at=CREATED,
        code_ref="examples/incident_triage/incident_triage.py",
        metadata={"consumer": "incident-triage"},
    )
    registry.put(experiment)
    context = EvaluationContext(dataset=dataset, candidate=candidate, namespace=run_id)
    deterministic = evaluate_generative(context, cases, outputs)
    judged = judge_metrics(
        context,
        tuple(
            JudgeResult(
                case_id=case.case_id,
                judge_id=judge["judge_id"],
                config_hash=judge["config_hash"],
                score=score,
                scale_min=judge["scale_min"],
                scale_max=judge["scale_max"],
            )
            for case, score in zip(cases, judge_scores, strict=True)
        ),
    )
    run = EvaluationRun(
        run_id=run_id,
        experiment_ref=experiment.ref,
        dataset_refs=(dataset.ref,),
        candidate_refs=(candidate.ref,),
        started_at=CREATED,
        completed_at=CREATED,
        code_ref="examples/incident_triage/incident_triage.py",
        config_hash=content_identity({"outputs": [value.metadata for value in outputs], "candidate": candidate.to_dict()}),
        metrics=deterministic + judged,
        metadata={"consumer": "incident-triage"},
    )
    registry.put(run)
    return run


def run_demo(registry_root: str | Path) -> dict:
    fixture = load_fixture()
    registry = FilesystemRegistry(registry_root)
    cases = tuple(_case(item) for item in fixture["cases"])
    baseline_outputs = tuple(_output(item) for item in fixture["baseline_outputs"])
    challenger_outputs = tuple(_output(item) for item in fixture["challenger_outputs"])

    dataset = DatasetRef(
        dataset_id="incident-triage-fixture",
        version="1",
        source="local-fixture",
        schema_id="incident-triage-v1",
        content_hash=content_identity(fixture["cases"]),
        created_at=CREATED,
    )
    baseline = CandidateRef(
        candidate_id="triage-prompt-v1",
        version="1",
        adapter="fixture:llm-prompt",
        created_at=CREATED,
        config_hash="prompt-config-v1",
        metadata={"candidate_type": "llm_prompt"},
    )
    challenger = CandidateRef(
        candidate_id="triage-agent-v2",
        version="2",
        adapter="fixture:tool-agent",
        created_at=CREATED,
        config_hash="agent-config-v2",
        metadata={"candidate_type": "tool_using_agent"},
    )
    for record in (dataset, baseline, challenger):
        registry.put(record)

    judge = fixture["judge"]
    baseline_run = _run(
        registry,
        dataset,
        baseline,
        cases,
        baseline_outputs,
        judge["baseline_scores"],
        judge,
        "incident-baseline",
    )
    challenger_run = _run(
        registry,
        dataset,
        challenger,
        cases,
        challenger_outputs,
        judge["challenger_scores"],
        judge,
        "incident-challenger",
    )

    findings = comparison_findings(baseline_run.metrics, challenger_run.metrics)
    for finding in findings:
        registry.put(finding)

    lifecycle = ChampionLifecycle(registry)
    initial = lifecycle.decide(
        decision_id="incident-baseline-accept",
        candidate_ref=baseline.ref,
        challenger_run_id=baseline_run.run_id,
        policy=PromotionPolicy("incident-triage", "1"),
        channel="incident-triage",
        created_at=CREATED,
    )
    promotion = lifecycle.decide(
        decision_id="incident-challenger-accept",
        candidate_ref=challenger.ref,
        challenger_run_id=challenger_run.run_id,
        incumbent_run_id=baseline_run.run_id,
        policy=PromotionPolicy(
            "incident-triage",
            "2",
            gates=(
                MetricGate("task_accuracy", min_value=0.75),
                MetricGate("structured_output_validity", min_value=1.0),
                MetricGate("tool_selection_accuracy", min_value=0.75),
                MetricGate("unsupported_claim_rate", max_value=0.0),
            ),
        ),
        channel="incident-triage",
        created_at=CREATED,
    )

    return {
        "dataset": dataset.to_dict(),
        "candidates": [baseline.to_dict(), challenger.to_dict()],
        "baseline_run": baseline_run.to_dict(),
        "challenger_run": challenger_run.to_dict(),
        "findings": [item.to_dict() for item in findings],
        "initial_decision": initial.to_dict(),
        "promotion_decision": promotion.to_dict(),
        "champion": lifecycle.current("incident-triage").to_dict(),
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        print(json.dumps(run_demo(directory), indent=2, sort_keys=True))
