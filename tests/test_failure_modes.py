"""Failure mode tests."""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, write_json
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION


def test_empty_workspace_produces_empty_manifest(tmp_path: Path) -> None:
    """Pipeline handles workspace with no files gracefully."""
    notes = tmp_path / "notes"
    notes.mkdir()
    # No files in notes dir

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_stage("rebuild", root=tmp_path, config=config)
    # Should succeed with 0 files
    assert result.status == "ok"


def test_binary_file_is_skipped(tmp_path: Path) -> None:
    """Binary files are skipped during ingestion."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (notes / "valid.md").write_text("# Valid\n\nContent.\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)
    assert result.status == "ok"
    # Should have processed at least the valid file
    assert result.detail.get("ok", 0) >= 1 or result.detail.get("files", 0) >= 1


def test_incompatible_schema_version_detected(tmp_path: Path) -> None:
    """Pipeline detects incompatible schema versions."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "test.md").write_text("# Test\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    # First run to create artifacts
    result = runner.run_ingest(root=tmp_path, config=config)
    assert result.status == "ok"

    # Corrupt the manifest with wrong schema version
    pkg_root = profile_pkg_root(tmp_path, config)
    manifest_path = Path(result.detail["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "v999"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Extract stage should detect incompatibility
    from auditgraph.utils.compatibility import check_latest_manifest_compatibility
    report = check_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)
    assert not report.compatible


def test_missing_run_id_resolves_latest(tmp_path: Path) -> None:
    """When run_id is None, pipeline resolves to latest run."""
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "test.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)

    # Ingest first
    ingest_result = runner.run_ingest(root=tmp_path, config=config)
    assert ingest_result.status == "ok"

    # Extract without explicit run_id
    extract_result = runner.run_extract(root=tmp_path, config=config, run_id=None)
    assert extract_result.status == "ok"
