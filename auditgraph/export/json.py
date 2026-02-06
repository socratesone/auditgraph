from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json, write_json


def _load_entities(pkg_root: Path) -> list[dict[str, object]]:
    entities_dir = pkg_root / "entities"
    entities: list[dict[str, object]] = []
    if not entities_dir.exists():
        return entities
    for path in entities_dir.rglob("*.json"):
        entities.append(read_json(path))
    return entities


def export_json(root: Path, pkg_root: Path, output_path: Path) -> Path:
    data = {
        "entities": _load_entities(pkg_root),
    }
    write_json(output_path, data)
    return output_path
