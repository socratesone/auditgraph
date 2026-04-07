"""Tests for NER link integration into the queryable graph.

The bug being fixed: NER links produced by extract_ner_entities() are
written to pkg_root/ner/links.json (a one-off intermediate artifact)
and never integrated into pkg_root/links/<shard>/*.json. As a result,
they don't appear in the link-types index, the adjacency index, or
the standard `auditgraph neighbors` query path.

After the fix, NER links MUST be written to the same sharded directory
as cooccurrence links, so all the standard query paths work uniformly.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root


def _make_mock_nlp():
    """Mock spaCy nlp that returns one PERSON entity per call."""
    fake_ent = MagicMock()
    fake_ent.text = "Alice Example"
    fake_ent.label_ = "PERSON"
    fake_ent.start_char = 0
    fake_ent.end_char = 13

    fake_ent2 = MagicMock()
    fake_ent2.text = "Bob Sample"
    fake_ent2.label_ = "PERSON"
    fake_ent2.start_char = 20
    fake_ent2.end_char = 30

    fake_doc = MagicMock()
    fake_doc.ents = [fake_ent, fake_ent2]

    return MagicMock(return_value=fake_doc)


def _setup_workspace_with_ner_enabled(tmp_path: Path) -> tuple[PipelineRunner, object, Path]:
    """Create a workspace with one markdown note and run ingest+normalize."""
    notes = tmp_path / "notes"
    notes.mkdir()
    note_path = notes / "test_note.md"
    note_path.write_text(
        "Alice Example met with Bob Sample at the meeting yesterday.\n"
        "They discussed the new project together.\n"
    )

    # Build a config with NER enabled and limited to notes/
    cfg_path = tmp_path / "test_config.yaml"
    cfg_path.write_text(
        "pkg_root: '.'\n"
        "active_profile: 'default'\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: ['notes']\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: ['.md']\n"
        "      ocr_mode: 'off'\n"
        "      chunk_tokens: 200\n"
        "      chunk_overlap_tokens: 40\n"
        "      max_file_size_bytes: 10000000\n"
        "    extraction:\n"
        "      ner:\n"
        "        enabled: true\n"
        "        model: 'mock_model'\n"
        "        quality_threshold: 0.0\n"
        "        natural_language_extensions: ['.md']\n"
        "        entity_types: ['PERSON']\n"
        "        cooccurrence_types: ['PERSON']\n"
    )

    config = load_config(cfg_path)
    runner = PipelineRunner()

    ingest = runner.run_ingest(root=tmp_path, config=config)
    assert ingest.status == "ok", f"ingest failed: {ingest.detail}"
    run_id = Path(str(ingest.detail["manifest"])).parent.name

    normalize = runner.run_normalize(root=tmp_path, config=config, run_id=run_id)
    assert normalize.status == "ok", f"normalize failed: {normalize.detail}"

    return runner, config, tmp_path


class TestNERLinksReachQueryableGraph:
    """The bug fix: NER links written by extract MUST be reachable through
    the standard link store, link-type index, and adjacency index."""

    def test_extract_writes_ner_links_to_links_dir(self, tmp_path, monkeypatch):
        """After extract, NER link files exist in pkg_root/links/<shard>/*.json."""
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: _make_mock_nlp(),
        )

        runner, config, root = _setup_workspace_with_ner_enabled(tmp_path)
        pkg_root = profile_pkg_root(root, config)
        run_id = list((pkg_root / "runs").iterdir())[0].name

        extract = runner.run_extract(root=root, config=config, run_id=run_id)
        assert extract.status == "ok", f"extract failed: {extract.detail}"

        link_files = list((pkg_root / "links").rglob("*.json")) if (pkg_root / "links").exists() else []
        assert len(link_files) > 0, (
            f"Expected NER link files in {pkg_root / 'links'}; found none. "
            f"This is the bug being fixed."
        )

    def test_no_orphaned_ner_links_artifact(self, tmp_path, monkeypatch):
        """The vestigial pkg_root/ner/links.json artifact should NOT be created.

        Before the fix, NER links were written there and never read.
        After the fix, they go to the canonical links/ directory.
        """
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: _make_mock_nlp(),
        )

        runner, config, root = _setup_workspace_with_ner_enabled(tmp_path)
        pkg_root = profile_pkg_root(root, config)
        run_id = list((pkg_root / "runs").iterdir())[0].name

        runner.run_extract(root=root, config=config, run_id=run_id)

        orphaned = pkg_root / "ner" / "links.json"
        assert not orphaned.exists(), (
            f"Vestigial intermediate artifact {orphaned} was created. "
            f"After the fix, NER links should go directly to links/ instead."
        )

    def test_ner_link_types_appear_in_link_type_index(self, tmp_path, monkeypatch):
        """After the index stage, indexes/link-types/ MUST include NER link types
        (MENTIONED_IN, CO_OCCURS_WITH) so users can query them."""
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: _make_mock_nlp(),
        )

        runner, config, root = _setup_workspace_with_ner_enabled(tmp_path)
        pkg_root = profile_pkg_root(root, config)
        run_id = list((pkg_root / "runs").iterdir())[0].name

        runner.run_extract(root=root, config=config, run_id=run_id)
        link_result = runner.run_link(root=root, config=config, run_id=run_id)
        assert link_result.status == "ok", f"link failed: {link_result.detail}"
        index_result = runner.run_index(root=root, config=config, run_id=run_id)
        assert index_result.status == "ok", f"index failed: {index_result.detail}"

        link_types_dir = pkg_root / "indexes" / "link-types"
        assert link_types_dir.exists(), "link-types index dir not created"

        link_type_files = {p.name for p in link_types_dir.glob("*.json")}
        assert "MENTIONED_IN.json" in link_type_files, (
            f"MENTIONED_IN link type not in index. Found: {sorted(link_type_files)}"
        )
        assert "CO_OCCURS_WITH.json" in link_type_files, (
            f"CO_OCCURS_WITH link type not in index. Found: {sorted(link_type_files)}"
        )

    def test_ner_edges_appear_in_adjacency_index(self, tmp_path, monkeypatch):
        """After index stage, the adjacency map MUST contain entries for NER
        entities so `auditgraph neighbors` can traverse them."""
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: _make_mock_nlp(),
        )

        runner, config, root = _setup_workspace_with_ner_enabled(tmp_path)
        pkg_root = profile_pkg_root(root, config)
        run_id = list((pkg_root / "runs").iterdir())[0].name

        runner.run_extract(root=root, config=config, run_id=run_id)
        runner.run_link(root=root, config=config, run_id=run_id)
        runner.run_index(root=root, config=config, run_id=run_id)

        adj_path = pkg_root / "indexes" / "graph" / "adjacency.json"
        assert adj_path.exists(), "adjacency index not created"
        adj = json.loads(adj_path.read_text())

        # Find at least one ner: entity that appears as a from_id with edges
        ner_sources = [
            from_id for from_id in adj.keys() if from_id.startswith("ent_")
        ]
        assert len(ner_sources) > 0, (
            "No source entities in adjacency index — links not being indexed"
        )

        # Verify at least one of these has a MENTIONED_IN or CO_OCCURS_WITH edge
        found_ner_edge = False
        for from_id, edges in adj.items():
            for edge in edges:
                if edge.get("type") in ("MENTIONED_IN", "CO_OCCURS_WITH"):
                    found_ner_edge = True
                    break
            if found_ner_edge:
                break
        assert found_ner_edge, (
            "Adjacency index has no MENTIONED_IN or CO_OCCURS_WITH edges. "
            "NER links are still stranded outside the queryable graph."
        )
