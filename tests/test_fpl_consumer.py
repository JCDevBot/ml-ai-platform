from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ml_ai_platform.contracts import Decision
from ml_ai_platform.registry import FilesystemRegistry


ROOT = Path(__file__).resolve().parents[1]
CONSUMER_PATH = ROOT / "examples" / "fpl_consumer" / "fpl_consumer.py"


def _consumer_module():
    spec = importlib.util.spec_from_file_location("fpl_consumer_example", CONSUMER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fpl_consumer_is_temporal_reproducible_and_uses_platform(tmp_path):
    consumer = _consumer_module()
    result = consumer.run_demo(tmp_path)

    assert result["training_dataset"]["dataset_id"] == "fpl-2025-26-gw37-cutoff"
    assert result["evaluation_dataset"]["dataset_id"] == "fpl-2025-26-gw38-resolved"
    assert result["evaluation_dataset"]["parents"] == [{"id": "fpl-2025-26-gw37-cutoff", "version": "1"}]
    assert result["leakage_guard"] == {
        "training_as_of": "2026-05-20T00:00:00+00:00",
        "evaluation_resolved_as_of": "2026-05-25T00:00:00+00:00",
        "training_uses_gameweeks": [36, 37],
        "prediction_features_gameweek": 37,
        "labels_gameweek": 38,
    }

    adapters = {item["adapter"] for item in result["candidates"]}
    assert adapters == {"heuristic:last-gameweek-points", "linear:ridge"}

    assert result["baseline"]["mae"] == pytest.approx(2 / 13)
    assert result["learned"]["mae"] == pytest.approx(0.42392417512963554)
    assert result["learned"]["mae"] > result["baseline"]["mae"]
    assert any(item["kind"] == "regression" and item["evidence"]["metric_name"] == "mae" for item in result["findings"])

    assert result["initial_decision"]["decision"] == Decision.ACCEPT.value
    assert result["challenger_decision"]["decision"] == Decision.REJECT.value
    assert result["champion"]["candidate_ref"] == {"id": "fpl-last-gameweek-points", "version": "1"}

    registry = FilesystemRegistry(tmp_path)
    baseline_run = registry.get_evaluation_run("fpl-gw38-baseline")
    learned_run = registry.get_evaluation_run("fpl-gw38-ridge")
    baseline_names = {metric.name for metric in baseline_run.metrics}
    learned_names = {metric.name for metric in learned_run.metrics}
    for names in (baseline_names, learned_names):
        assert {"mae", "rmse", "brier_score", "log_loss", "calibration_error"}.issubset(names)
    assert {metric.slice_id for metric in learned_run.metrics if metric.slice_id} == {"DEF", "FWD", "MID"}


def test_fpl_specific_logic_stays_outside_core_package():
    core = ROOT / "src" / "ml_ai_platform"
    offenders = []
    for path in core.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        if "fantasy premier league" in text or "fpl-" in text or '"fpl"' in text or "'fpl'" in text:
            offenders.append(path.relative_to(ROOT))
    assert offenders == []


def test_fixture_is_pinned_to_exact_source_file_versions():
    consumer = _consumer_module()
    fixture = consumer.load_fixture()
    files = fixture["source"]["files"]
    assert files == {
        "gw36": {
            "path": "data/2025-26/gws/gw36.csv",
            "sha": "d4aca0065019a72e91e56c72159ee98b17197e7a",
        },
        "gw37": {
            "path": "data/2025-26/gws/gw37.csv",
            "sha": "c39dfc812fedb85f9d4ce6fe48111ee65472c66a",
        },
        "gw38": {
            "path": "data/2025-26/gws/gw38.csv",
            "sha": "50af1ac211090656083104f521170dcec0a8a285",
        },
    }
