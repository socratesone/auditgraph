"""Spec-028 FR-016c/FR-016d · stale-entity pruning tests (invariant I9).

When a markdown source is re-extracted, the pipeline MUST:
 1. Delete every on-disk ag:section/ag:technology/ag:reference entity
    whose refs[0].source_path matches the current source.
 2. Delete every link whose rule_id is one of the four markdown rule IDs
    AND whose from_id or to_id is in the set of deleted entity IDs.

Pruning is strictly type-scoped — other entity types (note, NER, git
provenance) MUST NOT be touched.
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
        "      allowed_extensions: [.md]\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def _run_full_pipeline(root: Path, config_path: Path) -> None:
    """Run ingest + extract, threading the fresh run_id through to extract.

    `_resolve_run_id` picks the lexicographically highest directory name,
    NOT the most recent run. When the corpus changes between calls, the
    lex-pick may land on a stale manifest that no longer matches the
    on-disk document payloads. Passing `run_id` explicitly binds extract
    to the manifest the caller just produced.
    """
    import json as _json
    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=root, config=config)
    run_id = _json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    runner.run_extract(root=root, config=config, run_id=run_id)


def _load_entities_by_type(pkg_root: Path, entity_type: str) -> list[dict]:
    result = []
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return result
    for ent_file in entities_dir.rglob("*.json"):
        payload = json.loads(ent_file.read_text(encoding="utf-8"))
        if payload.get("type") == entity_type:
            result.append(payload)
    return result


def test_edit_heading_prunes_stale_section_entity(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Install\n\nbody\n", encoding="utf-8")

    _run_full_pipeline(tmp_path, config_path)
    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    sections_before = _load_entities_by_type(pkg_root, "ag:section")
    assert len(sections_before) == 1
    assert sections_before[0]["name"] == "Install"

    # Rename the heading.
    md_path.write_text("# Installation\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    sections_after = _load_entities_by_type(pkg_root, "ag:section")
    names = {s["name"] for s in sections_after}
    assert names == {"Installation"}, f"expected only 'Installation', got {names}"
    assert len(sections_after) == 1


def test_edit_adds_new_section_without_duplicating_old_one(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Install\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    md_path.write_text(
        "# Install\n\nbody\n\n## Prerequisites\n\nreqs\n", encoding="utf-8"
    )
    _run_full_pipeline(tmp_path, config_path)

    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    sections = _load_entities_by_type(pkg_root, "ag:section")
    names = {s["name"] for s in sections}
    assert names == {"Install", "Prerequisites"}, f"got {names}"


def test_pruning_scoped_to_ag_markdown_types_only(tmp_path: Path) -> None:
    """After an edit, the note entity for the same source MUST remain.

    The note's ID is derived from its canonical_key (stable across edits if
    the title doesn't change via frontmatter), so a content edit shouldn't
    remove it. Pruning is type-scoped (FR-016d).
    """
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Intro\n\nhello\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    notes_before = _load_entities_by_type(pkg_root, "ag:note")

    # Edit the body only; title unchanged ⇒ note ID stable.
    md_path.write_text("# Intro\n\ngoodbye\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    notes_after = _load_entities_by_type(pkg_root, "ag:note")
    assert {n["id"] for n in notes_after} == {n["id"] for n in notes_before}


def test_pruning_removes_orphan_markdown_links(tmp_path: Path) -> None:
    """After pruning stale entities, their markdown-rule links MUST be gone too."""
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Install\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    # Rename heading → old section ID goes stale. The contains_section
    # link that referenced the old section must be pruned too.
    md_path.write_text("# Installation\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    # Collect the single current ag:section ID.
    section_ids = {s["id"] for s in _load_entities_by_type(pkg_root, "ag:section")}
    assert len(section_ids) == 1

    # Every markdown-rule link whose to_id is a section must point at the
    # current section — no orphans.
    links_dir = pkg_root / "links"
    contains_links = []
    for lf in links_dir.rglob("*.json"):
        link = json.loads(lf.read_text(encoding="utf-8"))
        if link.get("rule_id") == "link.markdown.contains_section.v1":
            contains_links.append(link)
    for link in contains_links:
        assert link["to_id"] in section_ids, (
            f"orphan contains_section link survived pruning: {link}"
        )


def test_pruning_does_not_touch_ner_or_git_provenance_entities(tmp_path: Path) -> None:
    """Plant a fake git-provenance entity in entities/ and confirm it
    survives a markdown pruning pass."""
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Install\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)

    # Plant a fake commit entity that references notes/intro.md. Pruning
    # MUST NOT delete it (it's type="commit", not a markdown type).
    fake_commit = {
        "id": "commit_deadbeefabc123",
        "type": "commit",
        "name": "deadbeef",
        "refs": [
            {
                "source_path": "notes/intro.md",
                "source_hash": "d" * 64,
                "range": {"start_line": 1, "end_line": 1},
            }
        ],
    }
    from auditgraph.extract.manifest import write_entities

    write_entities(pkg_root, [fake_commit])

    # Edit markdown source, triggering a pruning pass for notes/intro.md.
    md_path.write_text("# Installation\n\nbody\n", encoding="utf-8")
    _run_full_pipeline(tmp_path, config_path)

    # The fake commit entity must still exist.
    all_entities = list((pkg_root / "entities").rglob("*.json"))
    commit_found = False
    for ent_file in all_entities:
        payload = json.loads(ent_file.read_text(encoding="utf-8"))
        if payload.get("id") == "commit_deadbeefabc123":
            commit_found = True
            break
    assert commit_found, "FR-016d violated: pruning deleted a non-markdown entity"
