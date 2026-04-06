from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from auditgraph.index.type_index import sanitize_type_name
from auditgraph.storage.artifacts import read_json


def _entity_path(pkg_root: Path, entity_id: str) -> Path:
    token = entity_id.split("_", 1)[-1]
    shard = token[:2] if token else entity_id[:2]
    return pkg_root / "entities" / shard / f"{entity_id}.json"


def load_entity(pkg_root: Path, entity_id: str) -> dict[str, object]:
    path = _entity_path(pkg_root, entity_id)
    return read_json(path)


def load_entities(pkg_root: Path, *, sorted_by_id: bool = False) -> list[dict[str, object]]:
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return []
    entities: list[dict[str, object]] = []
    for path in entities_dir.rglob("*.json"):
        entities.append(read_json(path))
    if sorted_by_id:
        entities.sort(key=lambda item: str(item.get("id", "")))
    return entities


def load_documents(pkg_root: Path) -> list[dict[str, object]]:
    documents_dir = pkg_root / "documents"
    if not documents_dir.exists():
        return []
    records: list[dict[str, object]] = []
    for path in sorted(documents_dir.rglob("*.json"), key=lambda item: item.as_posix()):
        records.append(read_json(path))
    return records


def load_chunks(pkg_root: Path) -> list[dict[str, object]]:
    chunks_dir = pkg_root / "chunks"
    if not chunks_dir.exists():
        return []
    records: list[dict[str, object]] = []
    for path in sorted(chunks_dir.rglob("*.json"), key=lambda item: item.as_posix()):
        records.append(read_json(path))
    return sorted(records, key=lambda item: (str(item.get("document_id", "")), int(item.get("order", 0))))


def load_entities_by_type(pkg_root: Path, entity_type: str) -> Iterator[dict[str, object]]:
    """Load entities of a specific type using the type index.

    Reads indexes/types/<sanitized_type>.json for the ID list,
    then loads each entity via load_entity().
    Yields dicts (generator, not list).
    """
    index_file = pkg_root / "indexes" / "types" / f"{sanitize_type_name(entity_type)}.json"
    if not index_file.exists():
        return
    entity_ids = json.loads(index_file.read_text())
    for entity_id in entity_ids:
        yield load_entity(pkg_root, entity_id)


def load_links(pkg_root: Path) -> Iterator[dict[str, object]]:
    """Iterate all link files. Generator over rglob('*.json')."""
    links_dir = pkg_root / "links"
    if not links_dir.exists():
        return
    for path in sorted(links_dir.rglob("*.json"), key=lambda p: p.name):
        yield json.loads(path.read_text())


def load_links_by_type(pkg_root: Path, link_type: str) -> Iterator[dict[str, object]]:
    """Load links of a specific type using the link-type index.

    Reads indexes/link-types/<sanitized_type>.json for the ID list,
    then loads each link file.
    Yields dicts.
    """
    index_file = pkg_root / "indexes" / "link-types" / f"{sanitize_type_name(link_type)}.json"
    if not index_file.exists():
        return
    link_ids = json.loads(index_file.read_text())
    links_dir = pkg_root / "links"
    for link_id in link_ids:
        token = link_id.split("_", 1)[-1]
        shard = token[:2] if token else link_id[:2]
        path = links_dir / shard / f"{link_id}.json"
        if path.exists():
            yield json.loads(path.read_text())
