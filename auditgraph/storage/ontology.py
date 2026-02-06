from __future__ import annotations

from typing import Any


def normalize_namespace(entity_type: str, primary: str, allow_secondary: bool) -> str:
    if ":" in entity_type:
        return entity_type if allow_secondary else f"{primary}:{entity_type.split(':', 1)[-1]}"
    return f"{primary}:{entity_type}"


def canonical_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def resolve_type(payload: dict[str, Any], primary: str, allow_secondary: bool) -> str:
    entity_type = str(payload.get("type", "entity"))
    return normalize_namespace(entity_type, primary, allow_secondary)
