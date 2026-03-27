from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.utils.paths import ensure_within_base
from auditgraph.utils.profile import validate_profile_name


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def profile_pkg_root(root: Path, config: Config) -> Path:
    profile = validate_profile_name(config.active_profile())
    base = root / ".pkg" / "profiles"
    target = base / profile
    ensure_within_base(target, base, label="profile pkg root")
    return target


def _document_path(pkg_root: Path, document_id: str) -> Path:
    return pkg_root / "documents" / f"{document_id}.json"


def _segment_path(pkg_root: Path, segment_id: str) -> Path:
    shard = segment_id[:2] if segment_id else "sg"
    return pkg_root / "segments" / shard / f"{segment_id}.json"


def _chunk_path(pkg_root: Path, chunk_id: str) -> Path:
    shard = chunk_id[:2] if chunk_id else "ch"
    return pkg_root / "chunks" / shard / f"{chunk_id}.json"


def write_document_artifacts(
    pkg_root: Path,
    document: dict[str, Any],
    segments: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> dict[str, Path]:
    document_id = str(document.get("document_id", ""))
    if not document_id:
        raise ValueError("document_id is required")

    doc_path = _document_path(pkg_root, document_id)
    if doc_path.exists():
        existing = read_json(doc_path)
        previous_hash = str(existing.get("source_hash", ""))
        if previous_hash:
            history = list(existing.get("hash_history", []))
            if previous_hash not in history:
                history.append(previous_hash)
            document["hash_history"] = sorted({*history, *document.get("hash_history", [])})
    write_json(doc_path, document)

    for segment in segments:
        segment_id = str(segment.get("segment_id", ""))
        if not segment_id:
            continue
        write_json(_segment_path(pkg_root, segment_id), segment)

    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id", ""))
        if not chunk_id:
            continue
        write_json(_chunk_path(pkg_root, chunk_id), chunk)

    return {
        "document": doc_path,
        "segments_root": pkg_root / "segments",
        "chunks_root": pkg_root / "chunks",
    }
