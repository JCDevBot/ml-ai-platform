"""Evidence-driven champion/challenger lifecycle management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import CandidateRef, Decision, PromotionDecision, RecordRef, canonical_json
from .evaluation import MetricGate, assess_challenger
from .registry import FilesystemRegistry, RecordAlreadyExists, RegistryError, write_atomic_text


class LifecycleError(RuntimeError):
    """Raised when lifecycle evidence or state is invalid."""


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleError(f"{name} must be a non-empty string")
    value = value.strip()
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise LifecycleError(f"{name} contains an unsafe path component")
    return value


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    """Versioned deterministic gates governing promotion eligibility."""

    policy_id: str
    version: str
    gates: tuple[MetricGate, ...] = ()
    require_human_review: bool = False
    allow_initial_promotion: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _required(self.version, "version"))

    @property
    def identity(self) -> str:
        return f"{self.policy_id}@{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "promotion_policy",
            "policy_id": self.policy_id,
            "version": self.version,
            "require_human_review": self.require_human_review,
            "allow_initial_promotion": self.allow_initial_promotion,
            "gates": [
                {
                    "metric_name": gate.metric_name,
                    "slice_id": gate.slice_id,
                    "min_value": gate.min_value,
                    "max_value": gate.max_value,
                    "max_regression": gate.max_regression,
                    "protected_slice": gate.protected_slice,
                }
                for gate in self.gates
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionPolicy":
        gates = tuple(
            MetricGate(
                metric_name=str(item["metric_name"]),
                slice_id=item.get("slice_id"),
                min_value=item.get("min_value"),
                max_value=item.get("max_value"),
                max_regression=item.get("max_regression"),
                protected_slice=bool(item.get("protected_slice", False)),
            )
            for item in data.get("gates", ())
        )
        return cls(
            policy_id=str(data["policy_id"]),
            version=str(data["version"]),
            gates=gates,
            require_human_review=bool(data.get("require_human_review", False)),
            allow_initial_promotion=bool(data.get("allow_initial_promotion", True)),
        )


@dataclass(frozen=True, slots=True)
class ChampionState:
    """Replaceable alias pointing to the current accepted champion evidence."""

    channel: str
    candidate_ref: RecordRef
    evaluation_run_id: str
    decision_id: str
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mlai.champion.v1",
            "channel": self.channel,
            "candidate_ref": {"id": self.candidate_ref.id, "version": self.candidate_ref.version},
            "evaluation_run_id": self.evaluation_run_id,
            "decision_id": self.decision_id,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChampionState":
        if data.get("schema_version") != "mlai.champion.v1":
            raise LifecycleError(f"unsupported champion state schema: {data.get('schema_version')!r}")
        ref = data["candidate_ref"]
        return cls(
            channel=_required(str(data["channel"]), "channel"),
            candidate_ref=RecordRef(id=str(ref["id"]), version=str(ref["version"])),
            evaluation_run_id=str(data["evaluation_run_id"]),
            decision_id=str(data["decision_id"]),
            updated_at=datetime.fromisoformat(str(data["updated_at"]).replace("Z", "+00:00")),
        )


class ChampionLifecycle:
    """Manage local champion aliases while preserving immutable evidence history."""

    def __init__(self, registry: FilesystemRegistry) -> None:
        self.registry = registry
        self.root = registry.root / "lifecycle"

    def save_policy(self, policy: PromotionPolicy) -> Path:
        """Persist one immutable versioned policy."""

        path = self.registry.root / "promotion-policies" / policy.policy_id / f"{policy.version}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json(policy.to_dict()) + "\n"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            existing = path.read_text(encoding="utf-8")
            if existing.strip() == payload.strip():
                return path
            raise RecordAlreadyExists(str(path.relative_to(self.registry.root))) from exc
        return path

    def load_policy(self, policy_id: str, version: str) -> PromotionPolicy:
        policy_id = _required(policy_id, "policy_id")
        version = _required(version, "version")
        path = self.registry.root / "promotion-policies" / policy_id / f"{version}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise LifecycleError(f"promotion policy not found: {policy_id}@{version}") from exc
        except json.JSONDecodeError as exc:
            raise LifecycleError(f"invalid promotion policy: {policy_id}@{version}") from exc
        if not isinstance(value, dict):
            raise LifecycleError("promotion policy must decode to an object")
        return PromotionPolicy.from_dict(value)

    def current(self, channel: str = "default") -> ChampionState | None:
        channel = _required(channel, "channel")
        path = self._state_path(channel)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise LifecycleError(f"invalid champion state for channel {channel}") from exc
        if not isinstance(value, dict):
            raise LifecycleError("champion state must decode to an object")
        state = ChampionState.from_dict(value)
        if state.channel != channel:
            raise LifecycleError("champion state channel does not match requested channel")
        return state

    def history(self, channel: str = "default") -> tuple[PromotionDecision, ...]:
        channel = _required(channel, "channel")
        records: list[PromotionDecision] = []
        for path in self.registry.iter_paths("promotion-decisions"):
            record = self.registry.get(path)
            if isinstance(record, PromotionDecision) and record.metadata.get("channel") == channel:
                records.append(record)
        records.sort(key=lambda item: (item.created_at, item.decision_id))
        return tuple(records)

    def decide(
        self,
        *,
        decision_id: str,
        candidate_ref: RecordRef,
        challenger_run_id: str,
        policy: PromotionPolicy,
        channel: str = "default",
        incumbent_run_id: str | None = None,
        created_at: datetime | None = None,
    ) -> PromotionDecision:
        """Evaluate a challenger, persist the decision, and update the alias only on accept."""

        channel = _required(channel, "channel")
        decision_id = _required(decision_id, "decision_id")
        challenger_run_id = _required(challenger_run_id, "challenger_run_id")
        candidate = self.registry.get_candidate(candidate_ref.id, candidate_ref.version)
        challenger = self.registry.get_evaluation_run(challenger_run_id)
        self._require_run_candidate(challenger.candidate_refs, candidate.ref, "challenger")
        incumbent = self.current(channel)

        reasons: list[str] = []
        result = Decision.ACCEPT
        incumbent_ref = incumbent.candidate_ref if incumbent else None

        if incumbent is None:
            if not policy.allow_initial_promotion:
                result = Decision.REVIEW
                reasons.append("initial promotion requires human review")
            elif any(gate.max_regression is not None for gate in policy.gates):
                result = Decision.REVIEW
                reasons.append("regression gates require incumbent evaluation evidence")
            else:
                assessment = assess_challenger((), challenger.metrics, policy.gates)
                if not assessment.eligible:
                    result = Decision.REJECT
                    reasons.extend(assessment.rejection_reasons)
        else:
            if incumbent_run_id is None:
                result = Decision.REVIEW
                reasons.append("incumbent evaluation evidence is required")
            else:
                baseline = self.registry.get_evaluation_run(_required(incumbent_run_id, "incumbent_run_id"))
                self._require_run_candidate(baseline.candidate_refs, incumbent.candidate_ref, "incumbent")
                assessment = assess_challenger(baseline.metrics, challenger.metrics, policy.gates)
                if not assessment.eligible:
                    result = Decision.REJECT
                    reasons.extend(assessment.rejection_reasons)

        if result == Decision.ACCEPT and policy.require_human_review:
            result = Decision.REVIEW
            reasons.append("promotion policy requires human review")
        if result == Decision.ACCEPT:
            reasons.append("challenger satisfied promotion policy")

        decision = PromotionDecision(
            decision_id=decision_id,
            candidate_ref=candidate.ref,
            evaluation_run_id=challenger.run_id,
            policy_version=policy.identity,
            decision=result,
            created_at=created_at or _now(),
            reasons=tuple(reasons),
            incumbent_ref=incumbent_ref,
            metadata={"channel": channel, "action": "promotion", "policy_id": policy.policy_id},
        )
        self.registry.put(decision)
        if decision.decision == Decision.ACCEPT:
            self._write_state(
                ChampionState(
                    channel=channel,
                    candidate_ref=candidate.ref,
                    evaluation_run_id=challenger.run_id,
                    decision_id=decision.decision_id,
                    updated_at=decision.created_at,
                )
            )
        return decision

    def rollback(
        self,
        *,
        decision_id: str,
        target_ref: RecordRef,
        evaluation_run_id: str,
        channel: str = "default",
        policy_version: str = "rollback@1",
        created_at: datetime | None = None,
    ) -> PromotionDecision:
        """Restore a previously accepted champion by appending new evidence."""

        channel = _required(channel, "channel")
        decision_id = _required(decision_id, "decision_id")
        current = self.current(channel)
        if current is None:
            raise LifecycleError("cannot rollback a channel without a current champion")
        previous_accepts = [
            item
            for item in self.history(channel)
            if item.decision == Decision.ACCEPT and item.candidate_ref == target_ref
        ]
        if not previous_accepts:
            raise LifecycleError("rollback target was not previously accepted for this channel")
        self.registry.get_candidate(target_ref.id, target_ref.version)
        evidence = self.registry.get_evaluation_run(_required(evaluation_run_id, "evaluation_run_id"))
        self._require_run_candidate(evidence.candidate_refs, target_ref, "rollback target")
        timestamp = created_at or _now()
        decision = PromotionDecision(
            decision_id=decision_id,
            candidate_ref=target_ref,
            evaluation_run_id=evidence.run_id,
            policy_version=_required(policy_version, "policy_version"),
            decision=Decision.ACCEPT,
            created_at=timestamp,
            reasons=("rollback to previously accepted champion",),
            incumbent_ref=current.candidate_ref,
            metadata={"channel": channel, "action": "rollback"},
        )
        self.registry.put(decision)
        self._write_state(
            ChampionState(
                channel=channel,
                candidate_ref=target_ref,
                evaluation_run_id=evidence.run_id,
                decision_id=decision.decision_id,
                updated_at=timestamp,
            )
        )
        return decision

    def _state_path(self, channel: str) -> Path:
        return self.root / "channels" / f"{channel}.json"

    def _write_state(self, state: ChampionState) -> None:
        write_atomic_text(self._state_path(state.channel), canonical_json(state.to_dict()) + "\n")

    @staticmethod
    def _require_run_candidate(run_refs: Sequence[RecordRef], expected: RecordRef, label: str) -> None:
        if expected not in run_refs:
            raise LifecycleError(
                f"{label} evaluation run does not reference candidate {expected.id}@{expected.version}"
            )
