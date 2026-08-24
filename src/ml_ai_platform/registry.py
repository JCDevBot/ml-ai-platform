"""Filesystem-backed immutable registry for lifecycle contracts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable

from .contracts import (
    CandidateRef,
    ContractMixin,
    DatasetRef,
    EvaluationRun,
    ExperimentSpec,
    Finding,
    PromotionDecision,
    contract_from_json,
)


class RegistryError(RuntimeError):
    """Base registry error."""


class RecordAlreadyExists(RegistryError):
    """Raised when an immutable registry key already exists."""


class RecordNotFound(RegistryError):
    """Raised when a requested registry key does not exist."""


class UnsupportedRecordType(RegistryError):
    """Raised when a contract has no persisted registry shape."""


_TOP_LEVEL_TYPES = (
    DatasetRef,
    CandidateRef,
    ExperimentSpec,
    EvaluationRun,
    Finding,
    PromotionDecision,
)


def _safe_component(value: str) -> str:
    if value in {"", ".", ".."} or "/" in value or "\\" in value:
        raise RegistryError(f"unsafe registry key component: {value!r}")
    return value


def registry_relative_path(record: ContractMixin) -> Path:
    """Return the deterministic storage key for a top-level record."""

    if isinstance(record, DatasetRef):
        return Path("datasets") / _safe_component(record.dataset_id) / f"{_safe_component(record.version)}.json"
    if isinstance(record, CandidateRef):
        return Path("candidates") / _safe_component(record.candidate_id) / f"{_safe_component(record.version)}.json"
    if isinstance(record, ExperimentSpec):
        return Path("experiments") / _safe_component(record.experiment_id) / f"{_safe_component(record.version)}.json"
    if isinstance(record, EvaluationRun):
        return Path("evaluation-runs") / f"{_safe_component(record.run_id)}.json"
    if isinstance(record, Finding):
        return Path("findings") / f"{_safe_component(record.finding_id)}.json"
    if isinstance(record, PromotionDecision):
        return Path("promotion-decisions") / f"{_safe_component(record.decision_id)}.json"
    raise UnsupportedRecordType(type(record).__name__)


class FilesystemRegistry:
    """Local registry that persists top-level contracts without mutation."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def put(self, record: ContractMixin) -> Path:
        """Persist one immutable record and return its path.

        Creation uses an exclusive file open, so concurrent writers cannot silently
        replace an existing registry record.
        """

        relative = registry_relative_path(record)
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = record.to_json() + "\n"

        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise RecordAlreadyExists(str(relative)) from exc
        return destination

    def get(self, relative_path: str | Path) -> ContractMixin:
        """Load a record by its registry-relative path."""

        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise RegistryError("relative_path must stay within the registry")
        source = self.root / relative
        try:
            payload = source.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RecordNotFound(str(relative)) from exc
        return contract_from_json(payload)

    def get_dataset(self, dataset_id: str, version: str) -> DatasetRef:
        return self._typed_get(Path("datasets") / _safe_component(dataset_id) / f"{_safe_component(version)}.json", DatasetRef)

    def get_candidate(self, candidate_id: str, version: str) -> CandidateRef:
        return self._typed_get(Path("candidates") / _safe_component(candidate_id) / f"{_safe_component(version)}.json", CandidateRef)

    def get_experiment(self, experiment_id: str, version: str) -> ExperimentSpec:
        return self._typed_get(Path("experiments") / _safe_component(experiment_id) / f"{_safe_component(version)}.json", ExperimentSpec)

    def get_evaluation_run(self, run_id: str) -> EvaluationRun:
        return self._typed_get(Path("evaluation-runs") / f"{_safe_component(run_id)}.json", EvaluationRun)

    def get_finding(self, finding_id: str) -> Finding:
        return self._typed_get(Path("findings") / f"{_safe_component(finding_id)}.json", Finding)

    def get_promotion_decision(self, decision_id: str) -> PromotionDecision:
        return self._typed_get(Path("promotion-decisions") / f"{_safe_component(decision_id)}.json", PromotionDecision)

    def iter_paths(self, collection: str) -> Iterable[Path]:
        """Yield registry-relative JSON paths in stable lexical order."""

        collection = _safe_component(collection)
        directory = self.root / collection
        if not directory.exists():
            return iter(())
        paths = sorted(path.relative_to(self.root) for path in directory.rglob("*.json"))
        return iter(paths)

    def _typed_get(self, relative: Path, expected_type):
        record = self.get(relative)
        if not isinstance(record, expected_type):
            raise RegistryError(
                f"registry record {relative} decoded as {type(record).__name__}, expected {expected_type.__name__}"
            )
        return record


def write_atomic_text(path: Path, payload: str) -> None:
    """Write replaceable non-registry metadata atomically.

    Registry records themselves never use this helper because they are immutable.
    It is exposed for future indexes/manifests that may be safely replaceable.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)
    temp_path.replace(path)
