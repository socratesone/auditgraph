from __future__ import annotations

ENTITY_TYPES = {
    "entity",
    "note",
    "task",
    "decision",
    "event",
}

CLAIM_TYPE = "claim"

REQUIRED_ENTITY_FIELDS = {"id", "type", "name", "canonical_key", "provenance"}
REQUIRED_CLAIM_FIELDS = {"id", "subject_id", "predicate", "object", "provenance"}
