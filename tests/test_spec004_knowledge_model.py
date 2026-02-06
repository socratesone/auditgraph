from __future__ import annotations

from auditgraph.storage.knowledge_models import (
    ClaimModel,
    EntityModel,
    ValidityWindow,
    apply_rule_confidence,
    flag_contradiction,
    validate_claim,
    validate_entity,
)
from auditgraph.storage.ontology import canonical_key, resolve_type


def test_validate_entity_and_claim() -> None:
    entity = EntityModel(
        id="ent_1",
        type="ag:note",
        name="Note",
        canonical_key="note",
        provenance={"source": "note.md"},
    )
    claim = ClaimModel(
        id="clm_1",
        subject_id="ent_1",
        predicate="mentions",
        object={"value": "x"},
        provenance={"source": "note.md"},
    )

    assert validate_entity(entity.to_dict()) == []
    assert validate_claim(claim.to_dict()) == []


def test_contradictions_and_confidence() -> None:
    claim = ClaimModel(
        id="clm_1",
        subject_id=None,
        predicate="states",
        object={"value": "x"},
        provenance={"source": "note.md"},
        validity_window=ValidityWindow(start="2020", end="2021"),
    )

    flagged = flag_contradiction(claim, "conflict")
    scored = apply_rule_confidence(flagged, 0.9)

    assert scored.contradiction is True
    assert scored.contradiction_reason == "conflict"
    assert scored.confidence == 0.9


def test_namespace_and_canonical_key() -> None:
    resolved = resolve_type({"type": "note"}, primary="ag", allow_secondary=True)

    assert resolved == "ag:note"
    assert canonical_key("My Note") == "my_note"
