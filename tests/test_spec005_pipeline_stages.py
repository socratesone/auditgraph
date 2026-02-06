from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import read_json, profile_pkg_root


def test_ingest_manifest_path_under_runs(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("# Note", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)

    manifest_path = Path(result.detail["manifest"])
    manifest = read_json(manifest_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    expected = pkg_root / "runs" / manifest["run_id"] / "ingest-manifest.json"

    assert manifest_path == expected


def test_rebuild_writes_stage_manifests(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("# Note", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_rebuild(root=tmp_path, config=config)

    assert result.status == "ok"
    run_id = result.detail["run_id"]
    pkg_root = profile_pkg_root(tmp_path, config)
    for stage in ("normalize", "extract", "link", "index"):
        manifest_path = pkg_root / "runs" / run_id / f"{stage}-manifest.json"
        manifest = read_json(manifest_path)
        assert manifest["stage"] == stage
