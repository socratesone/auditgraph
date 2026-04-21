"""Spec-028 US5 · `auditgraph node <id>` with ID-prefix dispatch.

Pre-028: this module searched `chunks/` via rglob then fell through to
`entities/`, leaving `documents/` completely uncovered. `auditgraph node
doc_xxx` surfaced a raw OSError like `[Errno 2] No such file or
directory`. BUG-4 from the Orpheus report.

Post-028: a table-driven prefix resolver tries the ID's prefix-expected
location first, then falls through to every other resolver, then
returns a structured not-found envelope. Behavior for existing ID
classes (chk_*, ent_*, commit_*, note_*, tag_*, author_*, file_*,
repo_*) is preserved — the only additive change is `doc_*` now works.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from auditgraph.storage.artifacts import read_json
from auditgraph.storage.loaders import load_entity


def _resolve_document(pkg_root: Path, entity_id: str) -> dict[str, Any] | None:
    doc_path = pkg_root / "documents" / f"{entity_id}.json"
    if not doc_path.exists():
        return None
    payload = read_json(doc_path)
    if not isinstance(payload, dict):
        return None
    return {
        "id": payload.get("document_id", entity_id),
        "type": "document",
        "name": payload.get("source_path") or entity_id,
        "source_path": payload.get("source_path"),
        "source_hash": payload.get("source_hash"),
        "mime_type": payload.get("mime_type"),
        "refs": [],
    }


def _resolve_chunk(pkg_root: Path, entity_id: str) -> dict[str, Any] | None:
    chunks_dir = pkg_root / "chunks"
    if not chunks_dir.exists():
        return None
    for path in chunks_dir.rglob(f"{entity_id}.json"):
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
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
    return None


def _resolve_entity(pkg_root: Path, entity_id: str) -> dict[str, Any] | None:
    """Use the existing sharded-entity loader; swallow FileNotFoundError
    so the caller can fall through cleanly."""
    try:
        entity = load_entity(pkg_root, entity_id)
    except FileNotFoundError:
        return None
    if not isinstance(entity, dict):
        return None
    return {
        "id": entity.get("id"),
        "type": entity.get("type"),
        "name": entity.get("name"),
        "refs": entity.get("refs", []),
    }


# Spec-028 US5 dispatch table. Prefix → resolver. Order matters for the
# prefix-match step; fall-through order is the same (resolvers are tried
# in list order when the prefix match yields nothing).
_DISPATCH: list[tuple[str, Callable[[Path, str], dict[str, Any] | None]]] = [
    ("doc_", _resolve_document),
    ("chk_", _resolve_chunk),
    # Everything else (ent_, commit_, tag_, ref_, author_, file_, repo_, note_)
    # falls through to _resolve_entity.
]

_FALLTHROUGH_RESOLVERS: tuple[Callable[[Path, str], dict[str, Any] | None], ...] = (
    _resolve_document,
    _resolve_chunk,
    _resolve_entity,
)


def node_view(pkg_root: Path, entity_id: str) -> dict[str, Any]:
    """Resolve `entity_id` to its on-disk record regardless of which
    subtree it lives under.

    Resolution order:
      1. If the ID starts with a registered prefix, try that prefix's
         resolver first.
      2. Fall through to every resolver in order (document, chunk, entity)
         — handles pathological cases where an ID's prefix doesn't match
         its on-disk location.
      3. If nothing resolves, return a structured not-found envelope —
         NOT a raw OSError.
    """
    # 1. Prefix-specific resolver.
    for prefix, resolver in _DISPATCH:
        if entity_id.startswith(prefix):
            view = resolver(pkg_root, entity_id)
            if view is not None:
                return view
            break  # preferred location missed; try fall-through.

    # 2. Fall-through.
    for resolver in _FALLTHROUGH_RESOLVERS:
        view = resolver(pkg_root, entity_id)
        if view is not None:
            return view

    # 3. Structured not-found envelope.
    return {
        "status": "error",
        "code": "not_found",
        "message": f"No node found for id '{entity_id}' in documents/, chunks/, or entities/.",
    }
