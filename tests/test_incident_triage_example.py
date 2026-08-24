from __future__ import annotations

import importlib.util
from pathlib import Path

from ml_ai_platform.contracts import Decision
from ml_ai_platform.registry import FilesystemRegistry


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "incident_triage" / "incident_triage.py"


def _module():
    spec = importlib.util.spec_from_file_location("incident_triage_example", EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _metrics(run: dict):
    return {item["name"]: item for item in run["metrics"]}


def test_incident_triage_comparison_produces_actionable_evidence_and_promotion(tmp_path):
    result = _module().run_demo(tmp_path)
    baseline = _metrics(result["baseline_run"])
    challenger = _metrics(result["challenger_run"])

    assert baseline["task_accuracy"]["value"] == 0.5
    assert challenger["task_accuracy"]["value"] == 1.0
    assert baseline["structured_output_validity"]["value"] == 0.75
    assert challenger["structured_output_validity"]["value"] == 1.0
    assert baseline["tool_selection_accuracy"]["value"] == 0.75
    assert challenger["tool_selection_accuracy"]["value"] == 1.0
    assert baseline["unsupported_claim_rate"]["value"] > 0
    assert challenger["unsupported_claim_rate"]["value"] == 0

    judge = challenger["judge_score"]
    assert judge["metadata"]["evidence_type"] == "judge_model"
    assert judge["metadata"]["authoritative_ground_truth"] is False
    assert judge["metadata"]["judge_id"] == "fixture-judge-v1"
    assert judge["metadata"]["judge_config_hash"] == "judge-config-001"

    kinds = {(item["kind"], item["evidence"]["metric_name"]) for item in result["findings"]}
    assert ("improvement", "task_accuracy") in kinds
    assert ("improvement", "tool_selection_accuracy") in kinds
    assert ("improvement", "unsupported_claim_rate") in kinds
    assert ("regression", "total_cost_units") in kinds

    assert result["initial_decision"]["decision"] == Decision.ACCEPT.value
    assert result["promotion_decision"]["decision"] == Decision.ACCEPT.value
    assert result["champion"]["candidate_ref"] == {"id": "triage-agent-v2", "version": "2"}

    adapters = {item["adapter"] for item in result["candidates"]}
    assert adapters == {"fixture:llm-prompt", "fixture:tool-agent"}

    registry = FilesystemRegistry(tmp_path)
    assert registry.get_evaluation_run("incident-challenger").candidate_refs[0].id == "triage-agent-v2"
    decisions = list(registry.iter_paths("promotion-decisions"))
    assert len(decisions) == 2
