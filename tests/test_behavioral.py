"""Behavioral tests validating meaningful graph outcomes."""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.keyword import keyword_search
from auditgraph.query.node_view import node_view
from auditgraph.query.neighbors import neighbors
from auditgraph.storage.artifacts import read_json, profile_pkg_root


def _run_pipeline(root: Path) -> tuple[Path, str]:
    """Run full pipeline and return (pkg_root, run_id)."""
    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_stage("rebuild", root=root, config=config)
    assert result.status == "ok"
    pkg_root = profile_pkg_root(root, config)
    return pkg_root, result.detail["run_id"]


def test_pipeline_creates_entities_from_markdown(tmp_path: Path) -> None:
    """Pipeline produces entities from markdown files."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "architecture.md").write_text(
        "# Architecture\n\nThe system uses microservices.\n",
        encoding="utf-8",
    )

    pkg_root, run_id = _run_pipeline(tmp_path)

    # Entities directory should have content (entities stored in hash-prefix subdirs)
    entities_dir = pkg_root / "entities"
    assert entities_dir.exists()
    entity_files = list(entities_dir.rglob("*.json"))
    assert len(entity_files) > 0

    # At least one entity should reference the source file via refs
    found_source = False
    for ef in entity_files:
        entity = read_json(ef)
        for ref in entity.get("refs", []):
            if "architecture.md" in str(ref.get("source_path", "")):
                found_source = True
                break
        if found_source:
            break
    assert found_source, "No entity references the source markdown file"


def test_keyword_search_finds_entities(tmp_path: Path) -> None:
    """Keyword search returns results for content that was ingested."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "auth.md").write_text(
        "# Authentication\n\nThe auth_token is validated on every request.\n",
        encoding="utf-8",
    )

    pkg_root, _ = _run_pipeline(tmp_path)
    results = keyword_search(pkg_root, "auth", enable_semantic=False)

    assert len(results) > 0, "Search should find results for ingested content"


def test_adjacency_index_is_created(tmp_path: Path) -> None:
    """Pipeline creates a graph adjacency index."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "module_a.py").write_text(
        "from module_b import helper\n\ndef process():\n    return helper()\n",
        encoding="utf-8",
    )
    (notes / "module_b.py").write_text(
        "def helper():\n    return 42\n",
        encoding="utf-8",
    )

    pkg_root, _ = _run_pipeline(tmp_path)

    adjacency_path = pkg_root / "indexes" / "graph" / "adjacency.json"
    assert adjacency_path.exists(), "Pipeline should produce adjacency index"
    adjacency = read_json(adjacency_path)
    assert isinstance(adjacency, dict)


def test_provenance_tracks_artifacts(tmp_path: Path) -> None:
    """Provenance records trace artifacts back to source files."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "test.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

    pkg_root, run_id = _run_pipeline(tmp_path)

    provenance_path = pkg_root / "provenance" / f"{run_id}.json"
    assert provenance_path.exists()
    records = read_json(provenance_path)
    assert len(records) > 0
    # Each record should have required provenance fields
    for record in records:
        assert "artifact_id" in record
        assert "source_path" in record
        assert "source_hash" in record
