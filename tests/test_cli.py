from __future__ import annotations

import json
from pathlib import Path

import yaml

from ml_ai_platform.cli import EXIT_ERROR, EXIT_POLICY_REJECTED, main
from ml_ai_platform.cli_io import CLI_SCHEMA_VERSION


def _write(path: Path, value: dict) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _run(capsys, registry: Path, *args: str):
    code = main(["--registry", str(registry), *args])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    return code, payload


def test_local_cli_end_to_end_with_policy_gate(tmp_path, capsys):
    registry = tmp_path / "registry"
    dataset_file = _write(
        tmp_path / "dataset.yaml",
        {
            "dataset_id": "synthetic-points",
            "version": "1",
            "source": "test-fixture",
            "schema_id": "points-v1",
            "content_hash": "sha256:fixture",
            "created_at": "2026-08-24T18:00:00+00:00",
        },
    )
    baseline_candidate_file = _write(
        tmp_path / "baseline.yaml",
        {
            "candidate_id": "baseline",
            "version": "1",
            "adapter": "fixture",
            "created_at": "2026-08-24T18:00:00+00:00",
            "code_ref": "test-baseline",
        },
    )
    challenger_candidate_file = _write(
        tmp_path / "challenger.yaml",
        {
            "candidate_id": "challenger",
            "version": "1",
            "adapter": "fixture",
            "created_at": "2026-08-24T18:00:00+00:00",
            "code_ref": "test-challenger",
        },
    )

    for kind, source in (
        ("dataset", dataset_file),
        ("candidate", baseline_candidate_file),
        ("candidate", challenger_candidate_file),
    ):
        code, payload = _run(capsys, registry, kind, "register", str(source))
        assert code == 0
        assert payload["schema_version"] == CLI_SCHEMA_VERSION
        assert payload["ok"] is True

    baseline_eval = _write(
        tmp_path / "baseline-eval.yaml",
        {
            "run_id": "baseline-run",
            "task": "regression",
            "dataset": {"dataset_id": "synthetic-points", "version": "1"},
            "candidate": {"candidate_id": "baseline", "version": "1"},
            "experiment": {"experiment_id": "points-baseline", "version": "1", "slice_ids": ["protected", "other"]},
            "truth": [0.0, 0.0, 10.0, 10.0],
            "predictions": [2.0, 2.0, 12.0, 12.0],
            "slices": ["protected", "protected", "other", "other"],
            "code_ref": "fixture-baseline",
        },
    )
    challenger_eval = _write(
        tmp_path / "challenger-eval.yaml",
        {
            "run_id": "challenger-run",
            "task": "regression",
            "dataset": {"dataset_id": "synthetic-points", "version": "1"},
            "candidate": {"candidate_id": "challenger", "version": "1"},
            "experiment": {"experiment_id": "points-challenger", "version": "1", "slice_ids": ["protected", "other"]},
            "truth": [0.0, 0.0, 10.0, 10.0],
            "predictions": [3.0, 3.0, 10.0, 10.0],
            "slices": ["protected", "protected", "other", "other"],
            "code_ref": "fixture-challenger",
        },
    )

    baseline_code, baseline_payload = _run(capsys, registry, "evaluate", str(baseline_eval))
    challenger_code, challenger_payload = _run(capsys, registry, "evaluate", str(challenger_eval))
    assert baseline_code == challenger_code == 0
    assert baseline_payload["data"]["run"]["run_id"] == "baseline-run"
    assert challenger_payload["data"]["run"]["run_id"] == "challenger-run"

    gates_file = _write(
        tmp_path / "gates.yaml",
        {
            "gates": [
                {
                    "metric_name": "mae",
                    "slice_id": "protected",
                    "max_regression": 0.5,
                    "protected_slice": True,
                }
            ]
        },
    )
    compare_code, compare_payload = _run(
        capsys,
        registry,
        "compare",
        "baseline-run",
        "challenger-run",
        "--gates",
        str(gates_file),
    )
    assert compare_code == EXIT_POLICY_REJECTED
    assert compare_payload["ok"] is False
    assert compare_payload["data"]["eligible"] is False
    assert any(item["kind"] == "protected_slice_regression" for item in compare_payload["data"]["findings"])

    report_code, report_payload = _run(capsys, registry, "report", "challenger-run")
    assert report_code == 0
    assert report_payload["data"]["run_id"] == "challenger-run"
    metric_names = {item["name"] for item in report_payload["data"]["metrics"]}
    assert {"mae", "rmse"}.issubset(metric_names)


def test_cli_invalid_input_is_machine_readable(tmp_path, capsys):
    bad = _write(tmp_path / "bad.yaml", {"dataset_id": "missing-fields"})
    code, payload = _run(capsys, tmp_path / "registry", "dataset", "register", str(bad))
    assert code == EXIT_ERROR
    assert payload["schema_version"] == CLI_SCHEMA_VERSION
    assert payload["ok"] is False
    assert payload["data"]["error_type"]
    assert payload["data"]["message"]


def test_cli_registration_is_idempotent_for_identical_contract(tmp_path, capsys):
    registry = tmp_path / "registry"
    candidate = _write(
        tmp_path / "candidate.yaml",
        {
            "candidate_id": "same",
            "version": "1",
            "adapter": "fixture",
            "created_at": "2026-08-24T18:00:00+00:00",
        },
    )
    first_code, _ = _run(capsys, registry, "candidate", "register", str(candidate))
    second_code, second_payload = _run(capsys, registry, "candidate", "register", str(candidate))
    assert first_code == second_code == 0
    assert second_payload["ok"] is True
