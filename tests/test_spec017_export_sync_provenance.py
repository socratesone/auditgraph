from __future__ import annotations

import shutil
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.export.json import export_json
from auditgraph.neo4j.export import export_neo4j
from auditgraph.neo4j.sync import sync_neo4j
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from tests.fixtures.neo4j_fixtures import FakeDriver
from tests.support import spec017_fixture_dir


def _prepare_docs(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = spec017_fixture_dir()
    for name in ("sample.pdf", "sample.docx"):
        shutil.copy2(fixture_dir / name, docs_dir / name)
    return docs_dir


def test_spec017_json_export_retains_provenance(tmp_path: Path) -> None:
    docs_dir = _prepare_docs(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    pkg_root = profile_pkg_root(tmp_path, config)
    output = tmp_path / "exports" / "subgraphs" / "spec017.json"
    export_json(tmp_path, pkg_root, output, config=config)

    payload = read_json(output)
    assert payload["documents"]
    assert payload["chunks"]
    assert payload["chunks"][0].get("source_path")


def test_spec017_neo4j_cypher_export_retains_provenance(tmp_path: Path) -> None:
    docs_dir = _prepare_docs(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    output = tmp_path / "exports" / "neo4j" / "spec017.cypher"
    export_neo4j(tmp_path, config, output_path=output)
    content = output.read_text(encoding="utf-8")
    assert "AuditgraphDocument" in content
    assert "AuditgraphChunk" in content
    assert "source_path" in content


def test_spec017_neo4j_sync_retains_provenance(tmp_path: Path, monkeypatch) -> None:
    docs_dir = _prepare_docs(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    store: dict[str, set[str]] = {"nodes": set(), "relationships": set()}
    monkeypatch.setattr(
        "auditgraph.neo4j.sync.load_connection_from_env",
        lambda: type("Conn", (), {"uri": "bolt://x", "database": "neo4j"})(),
    )
    monkeypatch.setattr("auditgraph.neo4j.sync.create_driver", lambda conn: FakeDriver(store))
    monkeypatch.setattr("auditgraph.neo4j.sync.ping_connection", lambda driver, db: None)

    summary = sync_neo4j(tmp_path, config, dry_run=False)
    assert summary.nodes_processed >= 2
    assert any(node.startswith("doc_") for node in store["nodes"])
    assert any(node.startswith("chk_") for node in store["nodes"])
