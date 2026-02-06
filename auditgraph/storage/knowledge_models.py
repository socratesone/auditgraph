from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from auditgraph.storage.knowledge_types import REQUIRED_CLAIM_FIELDS, REQUIRED_ENTITY_FIELDS


@dataclass(frozen=True)
class ValidityWindow:
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class EntityModel:
    id: str
    type: str
    name: str
    canonical_key: str
    provenance: dict[str, Any]
    aliases: list[str] | None = None
    refs: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimModel:
    id: str
    subject_id: str | None
    predicate: str
    object: Any
    provenance: dict[str, Any]
    confidence: float | None = None
    validity_window: ValidityWindow | None = None
    contradiction: bool = False
    contradiction_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_entity(payload: dict[str, Any]) -> list[str]:
    missing = sorted(REQUIRED_ENTITY_FIELDS - set(payload.keys()))
    return missing


def validate_claim(payload: dict[str, Any]) -> list[str]:
    missing = sorted(REQUIRED_CLAIM_FIELDS - set(payload.keys()))
    return missing


def flag_contradiction(claim: ClaimModel, reason: str) -> ClaimModel:
    return ClaimModel(
        id=claim.id,
        subject_id=claim.subject_id,
        predicate=claim.predicate,
        object=claim.object,
        provenance=claim.provenance,
        confidence=claim.confidence,
        validity_window=claim.validity_window,
        contradiction=True,
        contradiction_reason=reason,
    )


def apply_rule_confidence(claim: ClaimModel, score: float) -> ClaimModel:
    return ClaimModel(
        id=claim.id,
        subject_id=claim.subject_id,
        predicate=claim.predicate,
        object=claim.object,
        provenance=claim.provenance,
        confidence=score,
        validity_window=claim.validity_window,
        contradiction=claim.contradiction,
        contradiction_reason=claim.contradiction_reason,
    )
