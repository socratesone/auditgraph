from __future__ import annotations

from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.errors import CompatibilityError
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, write_json
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION
from auditgraph.utils.compatibility import check_latest_manifest_compatibility, ensure_latest_manifest_compatibility


def _write_manifest(pkg_root: Path, run_id: str, payload: dict[str, object]) -> None:
    manifest_path = pkg_root / "runs" / run_id / "ingest-manifest.json"
    write_json(manifest_path, payload)


def test_compatibility_no_manifest_is_ok(tmp_path: Path) -> None:
    pkg_root = profile_pkg_root(tmp_path, load_config(None))

    report = check_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)

    assert report.compatible is True
    assert report.artifact_version is None


def test_compatibility_missing_schema_version_is_incompatible(tmp_path: Path) -> None:
    pkg_root = profile_pkg_root(tmp_path, load_config(None))
    _write_manifest(pkg_root, "run_legacy", {"run_id": "run_legacy"})

    report = check_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)

    assert report.compatible is False
    assert report.artifact_version is None

    with pytest.raises(CompatibilityError):
        ensure_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)


def test_ingest_rejects_incompatible_manifest(tmp_path: Path) -> None:
    pkg_root = profile_pkg_root(tmp_path, load_config(None))
    _write_manifest(pkg_root, "run_legacy", {"run_id": "run_legacy", "schema_version": "v0"})

    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("# Note", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)

    with pytest.raises(CompatibilityError):
        runner.run_ingest(root=tmp_path, config=config)
