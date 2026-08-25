"""Local-only outbound connector contracts and prototype.

This module intentionally contains no production authentication implementation or network
client.  A connector is given an outbound transport adapter; tests use the in-memory fake
transport below.  Production credentials and hosted transport remain a separate human gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence


JsonScalar = None | bool | int | float | str
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ConnectorError(ValueError):
    """Raised when connector policy rejects an operation."""


class DataMovementMode(str, Enum):
    METADATA_ONLY = "metadata-only"
    UPLOAD = "upload"
    LOCAL_EXECUTION = "local-execution"


@dataclass(frozen=True, slots=True)
class ConnectorIdentity:
    """Revocable connector identity scoped to one workspace.

    The identity contains only local policy state.  It deliberately does not contain a
    token, password, API key, or other credential material.
    """

    connector_id: str
    workspace_id: str
    permissions: frozenset[str]
    created_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.connector_id.strip() or not self.workspace_id.strip():
            raise ConnectorError("connector_id and workspace_id are required")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ConnectorError("created_at must be timezone-aware")
        if self.revoked_at is not None:
            if self.revoked_at.tzinfo is None or self.revoked_at.utcoffset() is None:
                raise ConnectorError("revoked_at must be timezone-aware")
            if self.revoked_at < self.created_at:
                raise ConnectorError("revoked_at cannot precede created_at")

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, *, at: datetime | None = None) -> "ConnectorIdentity":
        when = at or datetime.now(timezone.utc)
        if not self.active:
            return self
        return replace(self, revoked_at=when)

    def allows(self, mode: DataMovementMode) -> bool:
        return f"movement:{mode.value}" in self.permissions


_DEFAULT_EXCLUDED_NAMES = frozenset(
    {
        ".env",
        ".ssh",
        ".aws",
        ".gnupg",
        ".git-credentials",
        "id_rsa",
        "id_ed25519",
        "credentials",
        "secrets",
        "secret",
        "private",
    }
)


@dataclass(frozen=True, slots=True)
class PathPolicy:
    """Explicit filesystem allow-list with conservative secret/private exclusions."""

    allowed_roots: tuple[Path, ...]
    excluded_names: frozenset[str] = _DEFAULT_EXCLUDED_NAMES

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise ConnectorError("at least one allowed root is required")
        normalized = tuple(Path(root).expanduser().resolve() for root in self.allowed_roots)
        object.__setattr__(self, "allowed_roots", normalized)

    def authorize(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        if not any(_is_within(candidate, root) for root in self.allowed_roots):
            raise ConnectorError(f"path is outside configured allow-list: {candidate}")

        lowered_parts = {part.lower() for part in candidate.parts}
        if lowered_parts.intersection(name.lower() for name in self.excluded_names):
            raise ConnectorError(f"path is excluded by secret/private policy: {candidate}")
        return candidate


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ConnectorEnvelope:
    """Bounded outbound message passed to a transport adapter."""

    connector_id: str
    workspace_id: str
    job_id: str
    mode: DataMovementMode
    metadata: tuple[ArtifactMetadata, ...] = ()
    uploads: tuple[bytes, ...] = ()
    result: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransportReceipt:
    accepted: bool
    message_id: str


class OutboundTransport(Protocol):
    """Transport boundary: connectors initiate sends; no inbound listener is defined."""

    def send(self, envelope: ConnectorEnvelope) -> TransportReceipt: ...


@dataclass(slots=True)
class FakeOutboundTransport:
    """Provider-free local transport used by tests and prototypes."""

    sent: list[ConnectorEnvelope] = field(default_factory=list)

    def send(self, envelope: ConnectorEnvelope) -> TransportReceipt:
        self.sent.append(envelope)
        return TransportReceipt(accepted=True, message_id=f"fake-{len(self.sent)}")


LocalExecutor = Callable[[], Mapping[str, JsonValue]]


@dataclass(slots=True)
class LocalConnector:
    identity: ConnectorIdentity
    path_policy: PathPolicy
    transport: OutboundTransport

    def submit(
        self,
        *,
        job_id: str,
        mode: DataMovementMode,
        source_paths: Sequence[str | Path] = (),
        executor: LocalExecutor | None = None,
    ) -> TransportReceipt:
        """Prepare a policy-bounded outbound envelope and send it.

        `metadata-only` hashes files but transfers no file bytes.
        `upload` transfers bytes only for explicitly supplied, allow-listed files.
        `local-execution` runs a caller-provided local function and transfers only its
        bounded result plus metadata; source bytes are never placed in the envelope.
        """

        if not job_id.strip():
            raise ConnectorError("job_id is required")
        if not self.identity.active:
            raise ConnectorError("connector identity is revoked")
        if not self.identity.allows(mode):
            raise ConnectorError(f"connector is not permitted for {mode.value}")

        authorized = tuple(self.path_policy.authorize(path) for path in source_paths)
        for path in authorized:
            if not path.is_file():
                raise ConnectorError(f"only explicit files may be submitted: {path}")

        metadata = tuple(_metadata(path) for path in authorized)
        uploads: tuple[bytes, ...] = ()
        result: Mapping[str, JsonValue] = {}

        if mode is DataMovementMode.UPLOAD:
            if not authorized:
                raise ConnectorError("upload requires at least one explicit file")
            uploads = tuple(path.read_bytes() for path in authorized)
        elif mode is DataMovementMode.LOCAL_EXECUTION:
            if executor is None:
                raise ConnectorError("local-execution requires an executor")
            raw_result = executor()
            result = _bounded_result(raw_result)
        elif executor is not None:
            raise ConnectorError("executor is only valid for local-execution")

        envelope = ConnectorEnvelope(
            connector_id=self.identity.connector_id,
            workspace_id=self.identity.workspace_id,
            job_id=job_id,
            mode=mode,
            metadata=metadata,
            uploads=uploads,
            result=result,
        )
        return self.transport.send(envelope)


def _metadata(path: Path) -> ArtifactMetadata:
    data = path.read_bytes()
    return ArtifactMetadata(path=str(path), size_bytes=len(data), sha256=sha256(data).hexdigest())


def _bounded_result(result: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    """Reject row-like raw-data keys from local-execution outbound results.

    This is intentionally conservative for the prototype.  Consumers can return metrics,
    findings, artifact references, summaries, and other bounded JSON, but not common raw-row
    containers.  Expanding this boundary requires an explicit policy change.
    """

    forbidden = {"rows", "records", "raw_rows", "examples", "samples"}
    conflicting = forbidden.intersection(key.lower() for key in result)
    if conflicting:
        raise ConnectorError(
            "local-execution result contains raw-row field(s): " + ", ".join(sorted(conflicting))
        )
    return dict(result)
