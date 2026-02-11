from __future__ import annotations

from pathlib import Path

from auditgraph.config import DEFAULT_CONFIG, load_config
from auditgraph.export.json import export_json
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.diff import diff_runs
from auditgraph.query.keyword import keyword_search
from auditgraph.scaffold import DEFAULT_DIRECTORIES, initialize_workspace
from auditgraph.storage.artifacts import read_json


def test_initialize_workspace_creates_structure(tmp_path: Path) -> None:
    config_source = tmp_path / "sample.yaml"
    config_source.write_text("profile: default\n", encoding="utf-8")

    created = initialize_workspace(tmp_path, config_source)

    for relative in DEFAULT_DIRECTORIES:
        assert (tmp_path / relative).exists()
    assert (tmp_path / "config" / "pkg.yaml").exists()
    assert any(path.endswith("config/pkg.yaml") for path in created)


def test_load_config_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.yaml")

    assert config.active_profile() == "default"
    assert config.raw == DEFAULT_CONFIG
    assert "include_paths" in config.profile()


def test_pipeline_ingest_smoke(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    note_path = notes_dir / "note.md"
    note_path.write_text("---\ntitle: Smoke Note\n---\nHello", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)

    assert result.status == "ok"
    manifest_path = Path(result.detail["manifest"])
    assert manifest_path.exists()

    manifest = read_json(manifest_path)
    assert manifest["ingested_count"] == 1
    assert manifest["skipped_count"] == 0

    record = manifest["records"][0]
    source_path = tmp_path / ".pkg" / "profiles" / "default" / "sources" / f"{record['source_hash']}.json"
    assert source_path.exists()


def test_export_json_empty_entities(tmp_path: Path) -> None:
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    output_path = tmp_path / "exports" / "subgraphs" / "export.json"

    export_json(tmp_path, pkg_root, output_path)

    payload = read_json(output_path)
    assert "entities" in payload
    assert payload["entities"] == []


def test_query_helpers_handle_missing_artifacts(tmp_path: Path) -> None:
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"

    assert keyword_search(pkg_root, "missing") == []
    assert diff_runs(pkg_root, "run-a", "run-b")["status"] == "missing_manifest"
