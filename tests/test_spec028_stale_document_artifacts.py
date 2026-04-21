"""Spec-028 adjustments3.md §4 · Stale document artifacts don't make
references internal.

A document file left on disk by a prior run, whose source is NOT in the
current ingest manifest, MUST NOT be indexed. References to that path
MUST classify as `unresolved`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.extract.markdown import (
    DocumentsIndex,
    RULE_RESOLVES_TO_DOCUMENT,
    extract_markdown_subentities,
)
from auditgraph.pipeline.runner import PipelineRunner, _build_documents_index
from auditgraph.storage.artifacts import profile_pkg_root, write_json
from auditgraph.utils.redaction import RedactionPolicy, Redactor


def _scaffold(tmp_path: Path) -> Path:
    (tmp_path / "notes").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def test_documents_index_by_source_path_excludes_stale_entries(tmp_path: Path) -> None:
    """Unit-level: _build_documents_index filters to current-run records only."""
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    (pkg_root / "documents").mkdir(parents=True)
    # Stale doc on disk with no corresponding current-run record.
    write_json(
        pkg_root / "documents" / "doc_ghost.json",
        {"document_id": "doc_ghost", "source_path": str(tmp_path / "notes" / "ghost.md"), "source_hash": "g" * 64, "mime_type": "text/markdown"},
    )
    # Current-run record does NOT include notes/ghost.md; only notes/intro.md.
    current_records = [
        {"path": "notes/intro.md", "source_hash": "i" * 64, "parse_status": "ok"},
    ]
    # The intro.md document file doesn't exist (test doesn't need it), so
    # the index should end up empty.
    index = _build_documents_index(pkg_root, tmp_path, current_records)
    assert index.by_source_path == {}
    assert "notes/ghost.md" not in index.by_source_path
    # And doc_ghost must not appear by-doc-id either.
    assert "doc_ghost" not in index.by_doc_id


def _run_pipeline(root: Path, config, runner: PipelineRunner) -> str:
    """Run ingest + extract, explicitly threading the fresh run_id so
    extract binds to the current manifest rather than `_resolve_run_id`'s
    lex-highest pick (which is non-deterministic across runs when the
    corpus changes).
    """
    ingest = runner.run_ingest(root=root, config=config)
    manifest_path = Path(ingest.detail["manifest"])
    run_id = json.loads(manifest_path.read_text(encoding="utf-8"))["run_id"]
    runner.run_extract(root=root, config=config, run_id=run_id)
    return run_id


def test_stale_doc_on_disk_does_not_classify_reference_as_internal(tmp_path: Path) -> None:
    """Full-pipeline test: a reference to a deleted-but-on-disk source
    classifies as unresolved, not internal.
    """
    config_path = _scaffold(tmp_path)

    # Two sources initially, with cross-refs.
    (tmp_path / "notes" / "intro.md").write_text(
        "See [setup](setup.md).\n", encoding="utf-8"
    )
    (tmp_path / "notes" / "setup.md").write_text(
        "# Setup\n\nbody.\n", encoding="utf-8"
    )

    config = load_config(config_path)
    runner = PipelineRunner()
    _run_pipeline(tmp_path, config, runner)

    pkg_root = profile_pkg_root(tmp_path, config)
    # Confirm the internal resolution worked on run 1.
    intro_refs = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in (pkg_root / "entities").rglob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("type") == "ag:reference"
    ]
    assert any(r["resolution"] == "internal" for r in intro_refs)

    # Delete setup.md's source file but leave its documents/<doc>.json on disk.
    (tmp_path / "notes" / "setup.md").unlink()
    _run_pipeline(tmp_path, config, runner)

    intro_refs_2 = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in (pkg_root / "entities").rglob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("type") == "ag:reference"
        and json.loads(p.read_text(encoding="utf-8")).get("target") == "setup.md"
    ]
    assert intro_refs_2, "expected to find the setup.md reference in intro"
    assert all(r["resolution"] == "unresolved" for r in intro_refs_2), (
        "stale doc on disk must not make references internal"
    )


def test_stale_doc_does_not_receive_resolves_to_document_link(tmp_path: Path) -> None:
    """No resolves_to_document edge should terminate at a stale doc_*."""
    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text(
        "See [setup](setup.md).\n", encoding="utf-8"
    )
    (tmp_path / "notes" / "setup.md").write_text("# Setup\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    _run_pipeline(tmp_path, config, runner)

    (tmp_path / "notes" / "setup.md").unlink()
    _run_pipeline(tmp_path, config, runner)

    pkg_root = profile_pkg_root(tmp_path, config)
    resolves_links = []
    for lf in (pkg_root / "links").rglob("*.json"):
        link = json.loads(lf.read_text(encoding="utf-8"))
        if link.get("rule_id") == RULE_RESOLVES_TO_DOCUMENT:
            resolves_links.append(link)

    # After the edit cycle, NO resolves_to_document link survives — the
    # one internal reference from run 1 was pruned (intro re-extracted),
    # and the new reference resolves as unresolved (setup.md not in the
    # current-run documents_index).
    assert resolves_links == [], (
        f"stale resolves_to_document link survived: {resolves_links}"
    )
