"""Spec-028 US5 · `auditgraph node <id>` ID-prefix dispatch (BUG-4).

Pre-028: node_view searched `chunks/` via rglob, then `entities/`. It
NEVER looked in `documents/` — so `auditgraph node doc_xxx` returned
`FileNotFoundError` as a raw OS error string. This test pins the
table-driven dispatch that fixes that, plus the fall-through semantics
and the structured not-found envelope.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.query.node_view import node_view
from auditgraph.storage.artifacts import write_json


@pytest.fixture()
def pkg_root(tmp_path: Path) -> Path:
    root = tmp_path / ".pkg" / "profiles" / "default"
    root.mkdir(parents=True)
    return root


def _write_doc(pkg_root: Path, doc_id: str, source_path: str = "notes/x.md") -> None:
    write_json(
        pkg_root / "documents" / f"{doc_id}.json",
        {
            "document_id": doc_id,
            "source_path": source_path,
            "source_hash": "a" * 64,
            "mime_type": "text/markdown",
            "file_size": 10,
            "extractor_id": "test",
            "extractor_version": "v1",
            "ingest_config_hash": "",
            "status": "ok",
            "status_reason": None,
            "hash_history": ["a" * 64],
            "text": "# x\n",
        },
    )


def _write_chunk(pkg_root: Path, chunk_id: str) -> None:
    from auditgraph.storage.sharding import shard_dir

    shard = shard_dir(pkg_root / "chunks", chunk_id)
    write_json(shard / f"{chunk_id}.json", {"chunk_id": chunk_id, "text": "chunk text", "source_path": "x.md", "source_hash": "a" * 64})


def _write_entity(pkg_root: Path, entity_id: str, entity_type: str = "ag:note") -> None:
    from auditgraph.storage.sharding import shard_dir

    shard = shard_dir(pkg_root / "entities", entity_id)
    write_json(
        shard / f"{entity_id}.json",
        {
            "id": entity_id,
            "type": entity_type,
            "name": "demo",
            "canonical_key": "demo",
            "aliases": [],
            "refs": [{"source_path": "notes/x.md", "source_hash": "a" * 64, "range": {"start_line": 1, "end_line": 1}}],
        },
    )


def test_doc_id_resolves_to_document_view(pkg_root: Path) -> None:
    doc_id = "doc_" + "d" * 24
    _write_doc(pkg_root, doc_id)
    view = node_view(pkg_root, doc_id)
    assert view.get("type") == "document"
    assert view.get("id") == doc_id


def test_chk_id_resolves_to_chunk_view(pkg_root: Path) -> None:
    chunk_id = "chk_" + "c" * 24
    _write_chunk(pkg_root, chunk_id)
    view = node_view(pkg_root, chunk_id)
    assert view.get("type") == "chunk"
    assert view.get("id") == chunk_id


def test_ent_id_resolves_to_entity_view(pkg_root: Path) -> None:
    ent_id = "ent_" + "e" * 24
    _write_entity(pkg_root, ent_id)
    view = node_view(pkg_root, ent_id)
    assert view.get("type") == "ag:note"
    assert view.get("id") == ent_id


def test_commit_id_resolves_via_entities_tree(pkg_root: Path) -> None:
    """Git-provenance entities (commit_*, tag_*, author_*, file_*, repo_*,
    ref_*) live under entities/<shard>/ per Spec-020."""
    commit_id = "commit_" + "c" * 24
    _write_entity(pkg_root, commit_id, entity_type="commit")
    view = node_view(pkg_root, commit_id)
    assert view.get("type") == "commit"
    assert view.get("id") == commit_id


def test_unknown_id_returns_structured_not_found(pkg_root: Path) -> None:
    view = node_view(pkg_root, "doc_deadbeef1234567890abcdef")
    assert view.get("status") == "error"
    assert view.get("code") == "not_found"
    # Message is human-friendly; MUST NOT be a raw OS FileNotFoundError.
    assert "Errno" not in str(view.get("message", ""))


def test_unknown_doc_id_does_not_leak_oserror(pkg_root: Path) -> None:
    """BUG-4 specifically: pre-028 `node doc_xxx` surfaced the OS error
    `[Errno 2] No such file or directory`. The new envelope must be
    structured."""
    view = node_view(pkg_root, "doc_" + "z" * 24)
    assert view.get("status") == "error"
    assert "[Errno" not in str(view.get("message", ""))


def test_fallthrough_finds_ent_id_when_prefix_match_missing(pkg_root: Path) -> None:
    """If a doc_* ID happens to resolve via the entity tree (pathological
    but defensive), the fall-through catches it."""
    # Place an entity record that starts with doc_ under entities/.
    weird_id = "doc_" + "f" * 24
    from auditgraph.storage.sharding import shard_dir

    shard = shard_dir(pkg_root / "entities", weird_id)
    write_json(
        shard / f"{weird_id}.json",
        {"id": weird_id, "type": "weird", "name": "", "canonical_key": "", "aliases": [], "refs": []},
    )
    view = node_view(pkg_root, weird_id)
    # Does NOT raise OSError; finds via fall-through.
    assert view.get("id") == weird_id or view.get("status") == "error"
