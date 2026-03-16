from __future__ import annotations

from pathlib import Path

from auditgraph.storage.loaders import load_entity
from auditgraph.storage.artifacts import read_json


def node_view(pkg_root: Path, entity_id: str) -> dict[str, object]:
    chunk_path = pkg_root / "chunks"
    if chunk_path.exists():
        for path in chunk_path.rglob(f"{entity_id}.json"):
            payload = read_json(path)
            return {
                "id": payload.get("chunk_id"),
                "type": "chunk",
                "name": payload.get("chunk_id"),
                "text": payload.get("text"),
                "citation": {
                    "source_path": payload.get("source_path"),
                    "source_hash": payload.get("source_hash"),
                    "page_start": payload.get("page_start"),
                    "page_end": payload.get("page_end"),
                    "paragraph_index_start": payload.get("paragraph_index_start"),
                    "paragraph_index_end": payload.get("paragraph_index_end"),
                },
                "refs": [],
            }

    entity = load_entity(pkg_root, entity_id)
    return {
        "id": entity.get("id"),
        "type": entity.get("type"),
        "name": entity.get("name"),
        "refs": entity.get("refs", []),
    }
