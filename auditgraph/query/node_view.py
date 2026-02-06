from __future__ import annotations

from pathlib import Path

from auditgraph.storage.loaders import load_entity


def node_view(pkg_root: Path, entity_id: str) -> dict[str, object]:
    entity = load_entity(pkg_root, entity_id)
    return {
        "id": entity.get("id"),
        "type": entity.get("type"),
        "name": entity.get("name"),
        "refs": entity.get("refs", []),
    }
