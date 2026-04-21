"""Spec-028 FR-016i · Opt-out preserves existing behavior.

When ``extraction.markdown.enabled == false``, BOTH the producer AND the
pruning helper MUST stay inert. Previously-emitted markdown sub-entities
remain on disk unchanged — disabling the feature does NOT retroactively
clean up the entity store.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root


def _scaffold(tmp_path: Path, markdown_enabled: bool) -> Path:
    (tmp_path / "notes").mkdir(exist_ok=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    flag = "true" if markdown_enabled else "false"
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n"
        "    extraction:\n"
        f"      markdown:\n        enabled: {flag}\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def _count_entities_by_type(pkg_root: Path, entity_type: str) -> int:
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return 0
    count = 0
    for ent_file in entities_dir.rglob("*.json"):
        payload = json.loads(ent_file.read_text(encoding="utf-8"))
        if payload.get("type") == entity_type:
            count += 1
    return count


def test_disabled_producer_emits_no_new_markdown_subentities(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path, markdown_enabled=False)
    (tmp_path / "notes" / "intro.md").write_text(
        "# Intro\n\nUse `Redis` and [setup](setup.md).\n", encoding="utf-8"
    )
    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    pkg_root = profile_pkg_root(tmp_path, config)
    # No markdown sub-entities on disk.
    for t in ("ag:section", "ag:technology", "ag:reference"):
        assert _count_entities_by_type(pkg_root, t) == 0, (
            f"disabled producer emitted {t}"
        )


def test_disabled_pruner_does_not_remove_existing_markdown_subentities(tmp_path: Path) -> None:
    """Seed markdown sub-entities with the flag enabled, then disable."""
    # Phase 1: enabled — emit sub-entities.
    config_path = _scaffold(tmp_path, markdown_enabled=True)
    (tmp_path / "notes" / "intro.md").write_text(
        "# Intro\n\nUse `Redis`.\n", encoding="utf-8"
    )
    config_a = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config_a)
    runner.run_extract(root=tmp_path, config=config_a)

    pkg_root = profile_pkg_root(tmp_path, config_a)
    n_sections_before = _count_entities_by_type(pkg_root, "ag:section")
    n_techs_before = _count_entities_by_type(pkg_root, "ag:technology")
    assert n_sections_before > 0
    assert n_techs_before > 0

    # Phase 2: disabled, edit the source so pruning WOULD fire if it were
    # active. FR-016i says it must not — existing entities stay.
    _scaffold(tmp_path, markdown_enabled=False)
    (tmp_path / "notes" / "intro.md").write_text(
        "# Introduction\n\nUse `PostgreSQL` now.\n", encoding="utf-8"
    )
    config_b = load_config(config_path)
    runner.run_ingest(root=tmp_path, config=config_b)
    runner.run_extract(root=tmp_path, config=config_b)

    n_sections_after = _count_entities_by_type(pkg_root, "ag:section")
    n_techs_after = _count_entities_by_type(pkg_root, "ag:technology")
    # Same counts — pruner stayed inert, producer stayed inert, nothing changed.
    assert n_sections_after == n_sections_before
    assert n_techs_after == n_techs_before


def test_enable_disable_cycle_leaves_prior_entities_on_disk(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path, markdown_enabled=True)
    (tmp_path / "notes" / "intro.md").write_text(
        "# Intro\n\nUse `Redis`.\n", encoding="utf-8"
    )
    runner = PipelineRunner()
    cfg_on = load_config(config_path)
    runner.run_ingest(root=tmp_path, config=cfg_on)
    runner.run_extract(root=tmp_path, config=cfg_on)

    pkg_root = profile_pkg_root(tmp_path, cfg_on)
    sections_first = _count_entities_by_type(pkg_root, "ag:section")

    # Disable; run again; nothing should change.
    _scaffold(tmp_path, markdown_enabled=False)
    cfg_off = load_config(config_path)
    runner.run_ingest(root=tmp_path, config=cfg_off)
    runner.run_extract(root=tmp_path, config=cfg_off)

    sections_after_off = _count_entities_by_type(pkg_root, "ag:section")
    assert sections_after_off == sections_first


def test_disabled_flag_still_runs_other_producers(tmp_path: Path) -> None:
    """Note entity (and other producers) must still emit when markdown is off."""
    config_path = _scaffold(tmp_path, markdown_enabled=False)
    (tmp_path / "notes" / "intro.md").write_text(
        "# Intro\n\nhello\n", encoding="utf-8"
    )
    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    pkg_root = profile_pkg_root(tmp_path, config)
    # The note entity is produced by build_note_entity — should still emit
    # regardless of the markdown sub-entity flag.
    assert _count_entities_by_type(pkg_root, "ag:note") > 0
