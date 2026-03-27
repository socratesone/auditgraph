"""Cross-run reproducibility tests."""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import read_json, profile_pkg_root


def _create_workspace(root: Path) -> None:
    notes = root / "notes"
    notes.mkdir(parents=True)
    (notes / "test.md").write_text("# Test Note\n\nSome content about testing.\n", encoding="utf-8")
    (notes / "code.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")


def test_reproducibility_across_runs(tmp_path: Path) -> None:
    """Two runs on identical input produce identical manifest hashes."""
    workspace_1 = tmp_path / "run1"
    workspace_2 = tmp_path / "run2"

    for ws in (workspace_1, workspace_2):
        _create_workspace(ws)

    runner = PipelineRunner()
    config = load_config(None)

    result_1 = runner.run_stage("rebuild", root=workspace_1, config=config)
    result_2 = runner.run_stage("rebuild", root=workspace_2, config=config)

    assert result_1.status == "ok"
    assert result_2.status == "ok"

    pkg_1 = profile_pkg_root(workspace_1, config)
    pkg_2 = profile_pkg_root(workspace_2, config)

    run_id_1 = result_1.detail["run_id"]
    run_id_2 = result_2.detail["run_id"]

    # Same input -> same run ID
    assert run_id_1 == run_id_2

    # Compare ingest manifests
    manifest_1 = read_json(pkg_1 / "runs" / run_id_1 / "ingest-manifest.json")
    manifest_2 = read_json(pkg_2 / "runs" / run_id_2 / "ingest-manifest.json")
    assert manifest_1["inputs_hash"] == manifest_2["inputs_hash"]
    assert manifest_1["outputs_hash"] == manifest_2["outputs_hash"]


def test_different_input_produces_different_run_id(tmp_path: Path) -> None:
    """Different input files produce different run IDs."""
    workspace_1 = tmp_path / "run1"
    workspace_2 = tmp_path / "run2"

    _create_workspace(workspace_1)
    notes_2 = workspace_2 / "notes"
    notes_2.mkdir(parents=True)
    (notes_2 / "different.md").write_text("# Different\n\nCompletely different content.\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)

    result_1 = runner.run_stage("rebuild", root=workspace_1, config=config)
    result_2 = runner.run_stage("rebuild", root=workspace_2, config=config)

    assert result_1.detail["run_id"] != result_2.detail["run_id"]
