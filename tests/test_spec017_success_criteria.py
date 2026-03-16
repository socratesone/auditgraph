from __future__ import annotations

import shutil
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.export.json import export_json
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from auditgraph.storage.loaders import load_chunks
from tests.support import spec017_fixture_dir


def _prepare_workspace(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = spec017_fixture_dir()
    for name in ("sample.pdf", "sample.docx", "scanned.pdf"):
        shutil.copy2(fixture_dir / name, docs_dir / name)
    return docs_dir


def test_sc001_determinism_and_unchanged_skip(tmp_path: Path) -> None:
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()

    first = runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])
    second = runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    first_manifest = read_json(Path(first.detail["manifest"]))
    second_manifest = read_json(Path(second.detail["manifest"]))
    assert first_manifest["run_id"] == second_manifest["run_id"]
    assert any(record.get("status_reason") == "unchanged_source_hash" for record in second_manifest["records"])


def test_sc002_citation_metadata_completeness(tmp_path: Path) -> None:
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    pkg_root = profile_pkg_root(tmp_path, config)
    chunks = load_chunks(pkg_root)
    assert chunks
    assert all(chunk.get("source_path") and chunk.get("source_hash") for chunk in chunks)


def test_sc003_failure_isolation_with_machine_readable_reasons(tmp_path: Path) -> None:
    docs_dir = _prepare_workspace(tmp_path)
    (docs_dir / "bad.doc").write_text("legacy", encoding="utf-8")

    config = load_config(None)
    runner = PipelineRunner()
    result = runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    manifest = read_json(Path(result.detail["manifest"]))
    failed = [record for record in manifest["records"] if record["parse_status"] == "failed"]
    ok = [record for record in manifest["records"] if record["parse_status"] == "ok"]
    assert failed
    assert ok
    assert all(isinstance(record.get("status_reason"), str) for record in failed)


def test_sc004_export_and_sync_provenance_retention(tmp_path: Path) -> None:
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    pkg_root = profile_pkg_root(tmp_path, config)
    output = tmp_path / "exports" / "subgraphs" / "spec017-success.json"
    export_json(tmp_path, pkg_root, output, config=config)
    payload = read_json(output)

    assert payload["documents"]
    assert payload["chunks"]
    assert all(item.get("source_path") for item in payload["chunks"])
