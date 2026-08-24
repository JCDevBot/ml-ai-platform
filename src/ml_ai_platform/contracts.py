"""Versioned domain-neutral contracts for ML/AI lifecycle records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Mapping


JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class ContractError(ValueError):
    """Raised when a lifecycle contract is invalid."""


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    REVIEW = "review"


class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    NEUTRAL = "neutral"


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _timezone_aware(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(f"{field_name} must be timezone-aware")
    return value


def _parse_datetime(value: str | datetime | None, field_name: str) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return _timezone_aware(value, field_name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field_name} must be an ISO-8601 timestamp") from exc
    return _timezone_aware(parsed, field_name)


def _json_safe(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        result = {key: _json_safe(item) for key, item in asdict(value).items()}
        record_type = getattr(value, "record_type", None)
        if record_type:
            result = {"record_type": record_type, **result}
        return result
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    raise ContractError(f"value of type {type(value).__name__} is not JSON serializable")


def canonical_json(value: Any) -> str:
    """Serialize a lifecycle record deterministically."""

    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_identity(value: Any) -> str:
    """Return a stable SHA-256 identity for a contract-compatible value."""

    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RecordRef:
    id: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required(self.id, "id"))
        object.__setattr__(self, "version", _required(self.version, "version"))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RecordRef":
        return cls(id=data["id"], version=data["version"])


class ContractMixin:
    record_type: ClassVar[str]

    def to_dict(self) -> dict[str, JsonValue]:
        value = _json_safe(self)
        if not isinstance(value, dict):
            raise ContractError("contract did not serialize to an object")
        return value

    def to_json(self) -> str:
        return canonical_json(self)


@dataclass(frozen=True, slots=True)
class DatasetRef(ContractMixin):
    record_type: ClassVar[str] = "dataset"

    dataset_id: str
    version: str
    source: str
    schema_id: str
    content_hash: str
    created_at: datetime
    as_of: datetime | None = None
    feature_version: str | None = None
    parents: tuple[RecordRef, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("dataset_id", "version", "source", "schema_id", "content_hash"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        _timezone_aware(self.created_at, "created_at")
        _timezone_aware(self.as_of, "as_of")
        if self.feature_version is not None:
            object.__setattr__(self, "feature_version", _required(self.feature_version, "feature_version"))
        _json_safe(self.metadata)

    @property
    def ref(self) -> RecordRef:
        return RecordRef(self.dataset_id, self.version)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DatasetRef":
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            source=data["source"],
            schema_id=data["schema_id"],
            content_hash=data["content_hash"],
            created_at=_parse_datetime(data["created_at"], "created_at"),
            as_of=_parse_datetime(data.get("as_of"), "as_of"),
            feature_version=data.get("feature_version"),
            parents=tuple(RecordRef.from_dict(item) for item in data.get("parents", ())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class CandidateRef(ContractMixin):
    record_type: ClassVar[str] = "candidate"

    candidate_id: str
    version: str
    adapter: str
    created_at: datetime
    artifact_uri: str | None = None
    code_ref: str | None = None
    config_hash: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("candidate_id", "version", "adapter"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        _timezone_aware(self.created_at, "created_at")
        for name in ("artifact_uri", "code_ref", "config_hash"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required(value, name))
        _json_safe(self.metadata)

    @property
    def ref(self) -> RecordRef:
        return RecordRef(self.candidate_id, self.version)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateRef":
        return cls(
            candidate_id=data["candidate_id"],
            version=data["version"],
            adapter=data["adapter"],
            created_at=_parse_datetime(data["created_at"], "created_at"),
            artifact_uri=data.get("artifact_uri"),
            code_ref=data.get("code_ref"),
            config_hash=data.get("config_hash"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ExperimentSpec(ContractMixin):
    record_type: ClassVar[str] = "experiment"

    experiment_id: str
    version: str
    dataset_refs: tuple[RecordRef, ...]
    candidate_refs: tuple[RecordRef, ...]
    evaluator_ids: tuple[str, ...]
    created_at: datetime
    baseline_candidate_refs: tuple[RecordRef, ...] = ()
    slice_ids: tuple[str, ...] = ()
    policy_version: str | None = None
    code_ref: str | None = None
    config_hash: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("experiment_id", "version"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not self.dataset_refs:
            raise ContractError("dataset_refs must contain at least one dataset")
        if not self.candidate_refs:
            raise ContractError("candidate_refs must contain at least one candidate")
        if not self.evaluator_ids:
            raise ContractError("evaluator_ids must contain at least one evaluator")
        object.__setattr__(self, "evaluator_ids", tuple(_required(item, "evaluator_id") for item in self.evaluator_ids))
        object.__setattr__(self, "slice_ids", tuple(_required(item, "slice_id") for item in self.slice_ids))
        _timezone_aware(self.created_at, "created_at")
        for name in ("policy_version", "code_ref", "config_hash"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required(value, name))
        _json_safe(self.metadata)

    @property
    def ref(self) -> RecordRef:
        return RecordRef(self.experiment_id, self.version)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExperimentSpec":
        return cls(
            experiment_id=data["experiment_id"],
            version=data["version"],
            dataset_refs=tuple(RecordRef.from_dict(item) for item in data["dataset_refs"]),
            candidate_refs=tuple(RecordRef.from_dict(item) for item in data["candidate_refs"]),
            evaluator_ids=tuple(data["evaluator_ids"]),
            created_at=_parse_datetime(data["created_at"], "created_at"),
            baseline_candidate_refs=tuple(RecordRef.from_dict(item) for item in data.get("baseline_candidate_refs", ())),
            slice_ids=tuple(data.get("slice_ids", ())),
            policy_version=data.get("policy_version"),
            code_ref=data.get("code_ref"),
            config_hash=data.get("config_hash"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class MetricResult(ContractMixin):
    record_type: ClassVar[str] = "metric"

    metric_id: str
    name: str
    value: float
    direction: MetricDirection = MetricDirection.NEUTRAL
    slice_id: str | None = None
    unit: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required(self.metric_id, "metric_id"))
        object.__setattr__(self, "name", _required(self.name, "name"))
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise ContractError("value must be numeric")
        object.__setattr__(self, "value", float(self.value))
        if not isinstance(self.direction, MetricDirection):
            object.__setattr__(self, "direction", MetricDirection(self.direction))
        if self.slice_id is not None:
            object.__setattr__(self, "slice_id", _required(self.slice_id, "slice_id"))
        if self.unit is not None:
            object.__setattr__(self, "unit", _required(self.unit, "unit"))
        _json_safe(self.metadata)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MetricResult":
        return cls(
            metric_id=data["metric_id"],
            name=data["name"],
            value=data["value"],
            direction=MetricDirection(data.get("direction", MetricDirection.NEUTRAL.value)),
            slice_id=data.get("slice_id"),
            unit=data.get("unit"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class Finding(ContractMixin):
    record_type: ClassVar[str] = "finding"

    finding_id: str
    kind: str
    severity: str
    message: str
    metric_ids: tuple[str, ...] = ()
    evidence: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("finding_id", "kind", "severity", "message"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "metric_ids", tuple(_required(item, "metric_id") for item in self.metric_ids))
        _json_safe(self.evidence)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Finding":
        return cls(
            finding_id=data["finding_id"],
            kind=data["kind"],
            severity=data["severity"],
            message=data["message"],
            metric_ids=tuple(data.get("metric_ids", ())),
            evidence=dict(data.get("evidence", {})),
        )


@dataclass(frozen=True, slots=True)
class EvaluationRun(ContractMixin):
    record_type: ClassVar[str] = "evaluation_run"

    run_id: str
    experiment_ref: RecordRef
    dataset_refs: tuple[RecordRef, ...]
    candidate_refs: tuple[RecordRef, ...]
    started_at: datetime
    code_ref: str
    config_hash: str
    metrics: tuple[MetricResult, ...] = ()
    findings: tuple[Finding, ...] = ()
    completed_at: datetime | None = None
    artifact_refs: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required(self.run_id, "run_id"))
        if not self.dataset_refs:
            raise ContractError("dataset_refs must contain at least one dataset")
        if not self.candidate_refs:
            raise ContractError("candidate_refs must contain at least one candidate")
        _timezone_aware(self.started_at, "started_at")
        _timezone_aware(self.completed_at, "completed_at")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ContractError("completed_at cannot precede started_at")
        object.__setattr__(self, "code_ref", _required(self.code_ref, "code_ref"))
        object.__setattr__(self, "config_hash", _required(self.config_hash, "config_hash"))
        object.__setattr__(self, "artifact_refs", tuple(_required(item, "artifact_ref") for item in self.artifact_refs))
        _json_safe(self.metadata)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvaluationRun":
        return cls(
            run_id=data["run_id"],
            experiment_ref=RecordRef.from_dict(data["experiment_ref"]),
            dataset_refs=tuple(RecordRef.from_dict(item) for item in data["dataset_refs"]),
            candidate_refs=tuple(RecordRef.from_dict(item) for item in data["candidate_refs"]),
            started_at=_parse_datetime(data["started_at"], "started_at"),
            code_ref=data["code_ref"],
            config_hash=data["config_hash"],
            metrics=tuple(MetricResult.from_dict(item) for item in data.get("metrics", ())),
            findings=tuple(Finding.from_dict(item) for item in data.get("findings", ())),
            completed_at=_parse_datetime(data.get("completed_at"), "completed_at"),
            artifact_refs=tuple(data.get("artifact_refs", ())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class PromotionDecision(ContractMixin):
    record_type: ClassVar[str] = "promotion_decision"

    decision_id: str
    candidate_ref: RecordRef
    evaluation_run_id: str
    policy_version: str
    decision: Decision
    created_at: datetime
    reasons: tuple[str, ...]
    incumbent_ref: RecordRef | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("decision_id", "evaluation_run_id", "policy_version"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not isinstance(self.decision, Decision):
            object.__setattr__(self, "decision", Decision(self.decision))
        _timezone_aware(self.created_at, "created_at")
        if not self.reasons:
            raise ContractError("reasons must contain at least one reason")
        object.__setattr__(self, "reasons", tuple(_required(item, "reason") for item in self.reasons))
        _json_safe(self.metadata)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionDecision":
        incumbent = data.get("incumbent_ref")
        return cls(
            decision_id=data["decision_id"],
            candidate_ref=RecordRef.from_dict(data["candidate_ref"]),
            evaluation_run_id=data["evaluation_run_id"],
            policy_version=data["policy_version"],
            decision=Decision(data["decision"]),
            created_at=_parse_datetime(data["created_at"], "created_at"),
            reasons=tuple(data["reasons"]),
            incumbent_ref=RecordRef.from_dict(incumbent) if incumbent else None,
            metadata=dict(data.get("metadata", {})),
        )


CONTRACT_TYPES = {
    DatasetRef.record_type: DatasetRef,
    CandidateRef.record_type: CandidateRef,
    ExperimentSpec.record_type: ExperimentSpec,
    EvaluationRun.record_type: EvaluationRun,
    Finding.record_type: Finding,
    PromotionDecision.record_type: PromotionDecision,
}


def contract_from_dict(data: Mapping[str, Any]) -> ContractMixin:
    """Deserialize a top-level lifecycle contract by its record type."""

    record_type = data.get("record_type")
    try:
        contract_type = CONTRACT_TYPES[record_type]
    except (KeyError, TypeError) as exc:
        raise ContractError(f"unsupported record_type: {record_type!r}") from exc
    return contract_type.from_dict(data)


def contract_from_json(payload: str) -> ContractMixin:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ContractError("invalid JSON payload") from exc
    if not isinstance(data, dict):
        raise ContractError("contract JSON must contain an object")
    return contract_from_dict(data)
