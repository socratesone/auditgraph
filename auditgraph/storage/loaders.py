from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json


def _entity_path(pkg_root: Path, entity_id: str) -> Path:
    token = entity_id.split("_", 1)[-1]
    shard = token[:2] if token else entity_id[:2]
    return pkg_root / "entities" / shard / f"{entity_id}.json"


def load_entity(pkg_root: Path, entity_id: str) -> dict[str, object]:
    path = _entity_path(pkg_root, entity_id)
    return read_json(path)


def load_entities(pkg_root: Path) -> list[dict[str, object]]:
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return []
    entities: list[dict[str, object]] = []
    for path in entities_dir.rglob("*.json"):
        entities.append(read_json(path))
    return entities
