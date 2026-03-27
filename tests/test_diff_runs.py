"""Tests for diff_runs: removed and changed path detection."""
from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.diff import diff_runs
from auditgraph.storage.artifacts import read_json
from tests.support import pkg_root


def _run_ingest(root: Path) -> dict[str, object]:
    runner = PipelineRunner()
    result = runner.run_ingest(root=root, config=load_config(None))
    return read_json(Path(result.detail["manifest"]))


def test_diff_detects_removed_paths(tmp_path: Path) -> None:
    """Ingest a+b, then ingest only a. b should appear in removed."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "a.md").write_text("File A", encoding="utf-8")
    (notes_dir / "b.md").write_text("File B", encoding="utf-8")

    manifest_ab = _run_ingest(tmp_path)

    # Remove b.md, re-ingest
    (notes_dir / "b.md").unlink()
    manifest_a = _run_ingest(tmp_path)

    payload = diff_runs(
        pkg_root(tmp_path), manifest_ab["run_id"], manifest_a["run_id"]
    )

    assert payload["status"] == "ok"
    assert "notes/b.md" in payload["removed"]
    assert "notes/a.md" not in payload["removed"]


def test_diff_detects_changed_paths(tmp_path: Path) -> None:
    """Ingest a with content v1, then ingest a with content v2. a should appear in changed."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "a.md").write_text("Version 1 content", encoding="utf-8")

    manifest_v1 = _run_ingest(tmp_path)

    # Modify a.md, re-ingest
    (notes_dir / "a.md").write_text("Version 2 content -- different", encoding="utf-8")
    manifest_v2 = _run_ingest(tmp_path)

    payload = diff_runs(
        pkg_root(tmp_path), manifest_v1["run_id"], manifest_v2["run_id"]
    )

    assert payload["status"] == "ok"
    assert "notes/a.md" in payload["changed"]
