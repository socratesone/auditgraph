from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json


def _entity_path(pkg_root: Path, entity_id: str) -> Path:
    return pkg_root / "entities" / entity_id[:2] / f"{entity_id}.json"


def load_entity(pkg_root: Path, entity_id: str) -> dict[str, object]:
    path = _entity_path(pkg_root, entity_id)
    return read_json(path)
