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


def test_us1_ingest_creates_manifest(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("Hello", encoding="utf-8")

    manifest = _run_ingest(tmp_path)

    assert manifest["run_id"].startswith("run_")


def test_us1_ingest_counts_records(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("Hello", encoding="utf-8")

    manifest = _run_ingest(tmp_path)

    assert manifest["records"]
    assert manifest["ingested_count"] == 1


def test_us7_rebuild_run_id_is_stable(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("Hello", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    first = runner.run_rebuild(root=tmp_path, config=config)
    second = runner.run_rebuild(root=tmp_path, config=config)

    first_manifest = read_json(Path(first.detail["manifest"]))
    second_manifest = read_json(Path(second.detail["manifest"]))

    assert first_manifest["run_id"] == second_manifest["run_id"]


def test_us7_rebuild_outputs_hash_is_stable(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("Hello", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    first = runner.run_rebuild(root=tmp_path, config=config)
    second = runner.run_rebuild(root=tmp_path, config=config)

    first_manifest = read_json(Path(first.detail["manifest"]))
    second_manifest = read_json(Path(second.detail["manifest"]))

    assert first_manifest["outputs_hash"] == second_manifest["outputs_hash"]


def test_us8_diff_detects_added_paths(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "a.md").write_text("A", encoding="utf-8")

    manifest_a = _run_ingest(tmp_path)

    (notes_dir / "b.md").write_text("B", encoding="utf-8")
    manifest_b = _run_ingest(tmp_path)

    payload = diff_runs(pkg_root(tmp_path), manifest_a["run_id"], manifest_b["run_id"])

    assert payload["status"] == "ok"
    assert "notes/b.md" in payload["added"]
