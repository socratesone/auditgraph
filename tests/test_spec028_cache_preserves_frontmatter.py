"""Spec-028 regression · Cache hits must not clobber source metadata.

Bug: on a cache-hit rerun, `run_ingest` wrote a minimal source metadata
dict (no frontmatter, no document/segments/chunks keys) to
`sources/<source_hash>.json` — OVERWRITING the rich metadata written by
the fresh run. The extract stage then fell back from the frontmatter
title to the filename stem, creating a SECOND note entity with a
different canonical_key. Result: a cached rerun silently duplicated the
note entity.

Fix: on a cache hit, preserve the existing source metadata — don't
overwrite it with the minimal record-only metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root


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
        "      allowed_extensions: [.md]\n"
        "      frontmatter_schema: [title, tags, project, status]\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def test_cache_hit_preserves_frontmatter_in_source_metadata(tmp_path: Path) -> None:
    """After a cache-hit rerun, sources/<hash>.json MUST still carry the
    frontmatter dict from the fresh parse."""
    config_path = _scaffold(tmp_path)
    md = tmp_path / "notes" / "intro.md"
    md.write_text(
        "---\ntitle: Fancy Title\ntags: [demo]\n---\n\n# Intro\n\nhello\n",
        encoding="utf-8",
    )

    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    pkg_root = profile_pkg_root(tmp_path, config)
    source_files = list((pkg_root / "sources").glob("*.json"))
    assert len(source_files) == 1
    source_meta_first = json.loads(source_files[0].read_text(encoding="utf-8"))
    assert source_meta_first.get("frontmatter", {}).get("title") == "Fancy Title"

    # Cache-hit rerun.
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    source_meta_second = json.loads(source_files[0].read_text(encoding="utf-8"))
    assert source_meta_second.get("frontmatter", {}).get("title") == "Fancy Title", (
        "cache-hit rerun clobbered source frontmatter — the subsequent extract "
        "would fall back to filename stem and duplicate the note entity"
    )


def test_cache_hit_produces_single_note_entity(tmp_path: Path) -> None:
    """The real user-facing assertion: two runs on the same markdown produce
    exactly ONE ag:note entity, not two."""
    config_path = _scaffold(tmp_path)
    md = tmp_path / "notes" / "intro.md"
    md.write_text(
        "---\ntitle: Fancy Title\n---\n\n# Intro\n\nhello\n",
        encoding="utf-8",
    )

    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    pkg_root = profile_pkg_root(tmp_path, config)
    note_entities = []
    for entity_file in (pkg_root / "entities").rglob("*.json"):
        payload = json.loads(entity_file.read_text(encoding="utf-8"))
        if payload.get("type") == "ag:note":
            note_entities.append(payload)
    names = {n["name"] for n in note_entities}
    assert len(note_entities) == 1, (
        f"expected exactly 1 note entity, got {len(note_entities)} with names={names!r}"
    )
    assert "Fancy Title" in names
