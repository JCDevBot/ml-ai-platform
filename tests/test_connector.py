from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ml_ai_platform.connector import (
    ConnectorError,
    ConnectorIdentity,
    DataMovementMode,
    FakeOutboundTransport,
    LocalConnector,
    PathPolicy,
)


NOW = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)


def _identity(*modes: DataMovementMode) -> ConnectorIdentity:
    return ConnectorIdentity(
        connector_id="connector-local-1",
        workspace_id="workspace-test",
        permissions=frozenset(f"movement:{mode.value}" for mode in modes),
        created_at=NOW,
    )


def _connector(root: Path, *modes: DataMovementMode) -> tuple[LocalConnector, FakeOutboundTransport]:
    transport = FakeOutboundTransport()
    connector = LocalConnector(
        identity=_identity(*modes),
        path_policy=PathPolicy((root,)),
        transport=transport,
    )
    return connector, transport


def test_metadata_only_sends_hashes_without_file_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text('{"mae":0.42}', encoding="utf-8")
    connector, transport = _connector(tmp_path, DataMovementMode.METADATA_ONLY)

    receipt = connector.submit(
        job_id="job-metadata",
        mode=DataMovementMode.METADATA_ONLY,
        source_paths=[artifact],
    )

    assert receipt.accepted
    envelope = transport.sent[0]
    assert envelope.mode is DataMovementMode.METADATA_ONLY
    assert envelope.uploads == ()
    assert envelope.result == {}
    assert envelope.metadata[0].size_bytes == len(artifact.read_bytes())
    assert len(envelope.metadata[0].sha256) == 64


def test_upload_requires_explicit_allowlisted_file(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    artifact = root / "model.bin"
    artifact.write_bytes(b"model-bytes")
    connector, transport = _connector(root, DataMovementMode.UPLOAD)

    connector.submit(job_id="job-upload", mode=DataMovementMode.UPLOAD, source_paths=[artifact])

    assert transport.sent[0].uploads == (b"model-bytes",)


def test_path_outside_allowlist_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    connector, _ = _connector(allowed, DataMovementMode.METADATA_ONLY)

    with pytest.raises(ConnectorError, match="outside configured allow-list"):
        connector.submit(
            job_id="job-outside",
            mode=DataMovementMode.METADATA_ONLY,
            source_paths=[outside],
        )


def test_secret_and_private_paths_are_excluded_by_default(tmp_path: Path) -> None:
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    secret = secret_dir / "id_rsa"
    secret.write_text("secret", encoding="utf-8")
    connector, _ = _connector(tmp_path, DataMovementMode.UPLOAD)

    with pytest.raises(ConnectorError, match="secret/private policy"):
        connector.submit(job_id="job-secret", mode=DataMovementMode.UPLOAD, source_paths=[secret])


def test_directories_cannot_be_recursively_ingested(tmp_path: Path) -> None:
    nested = tmp_path / "dataset"
    nested.mkdir()
    (nested / "rows.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    connector, _ = _connector(tmp_path, DataMovementMode.UPLOAD)

    with pytest.raises(ConnectorError, match="only explicit files"):
        connector.submit(job_id="job-dir", mode=DataMovementMode.UPLOAD, source_paths=[nested])


def test_mode_must_be_explicitly_permitted(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("data", encoding="utf-8")
    connector, _ = _connector(tmp_path, DataMovementMode.METADATA_ONLY)

    with pytest.raises(ConnectorError, match="not permitted"):
        connector.submit(job_id="job-upload", mode=DataMovementMode.UPLOAD, source_paths=[artifact])


def test_revoked_identity_cannot_submit(tmp_path: Path) -> None:
    connector, _ = _connector(tmp_path, DataMovementMode.METADATA_ONLY)
    connector.identity = connector.identity.revoke(at=NOW)

    with pytest.raises(ConnectorError, match="revoked"):
        connector.submit(job_id="job-revoked", mode=DataMovementMode.METADATA_ONLY)


def test_local_execution_returns_metrics_without_source_bytes(tmp_path: Path) -> None:
    rows = tmp_path / "evaluation.csv"
    rows.write_text("truth,prediction\n1,0.9\n0,0.1\n", encoding="utf-8")
    connector, transport = _connector(tmp_path, DataMovementMode.LOCAL_EXECUTION)

    connector.submit(
        job_id="job-local-execution",
        mode=DataMovementMode.LOCAL_EXECUTION,
        source_paths=[rows],
        executor=lambda: {"metrics": {"brier": 0.01}, "run_id": "run-123"},
    )

    envelope = transport.sent[0]
    assert envelope.uploads == ()
    assert envelope.result == {"metrics": {"brier": 0.01}, "run_id": "run-123"}
    assert b"truth,prediction" not in repr(envelope).encode()


def test_local_execution_rejects_raw_row_result_fields(tmp_path: Path) -> None:
    connector, transport = _connector(tmp_path, DataMovementMode.LOCAL_EXECUTION)

    with pytest.raises(ConnectorError, match="raw-row"):
        connector.submit(
            job_id="job-raw-rows",
            mode=DataMovementMode.LOCAL_EXECUTION,
            executor=lambda: {"rows": [{"secret": "value"}], "metrics": {"mae": 1.0}},
        )

    assert transport.sent == []


def test_fake_transport_requires_no_credentials(tmp_path: Path) -> None:
    connector, transport = _connector(tmp_path, DataMovementMode.METADATA_ONLY)

    connector.submit(job_id="job-no-creds", mode=DataMovementMode.METADATA_ONLY)

    assert transport.sent[0].connector_id == "connector-local-1"
    assert not hasattr(connector.identity, "token")
    assert not hasattr(connector.identity, "api_key")
