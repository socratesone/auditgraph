from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.neo4j.sync import sync_neo4j
from auditgraph.storage.artifacts import profile_pkg_root
from tests.fixtures.neo4j_fixtures import FakeDriver, write_test_graph


def test_sync_neo4j_dry_run_no_mutation(tmp_path: Path, monkeypatch) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)
    store = {"nodes": set(), "relationships": set()}

    monkeypatch.setattr(
        "auditgraph.neo4j.sync.load_connection_from_env",
        lambda **_kw: type("Conn", (), {"uri": "bolt://x", "database": "neo4j"})(),
    )
    monkeypatch.setattr("auditgraph.neo4j.sync.create_driver", lambda conn: FakeDriver(store))
    monkeypatch.setattr("auditgraph.neo4j.sync.ping_connection", lambda driver, db: None)

    summary = sync_neo4j(tmp_path, config, dry_run=True)
    assert summary.mode == "dry-run"
    assert store["nodes"] == set()
    assert store["relationships"] == set()


def test_sync_neo4j_repeated_runs_keep_unique_ids(tmp_path: Path, monkeypatch) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)
    store = {"nodes": set(), "relationships": set()}

    monkeypatch.setattr(
        "auditgraph.neo4j.sync.load_connection_from_env",
        lambda **_kw: type("Conn", (), {"uri": "bolt://x", "database": "neo4j"})(),
    )
    monkeypatch.setattr("auditgraph.neo4j.sync.create_driver", lambda conn: FakeDriver(store))
    monkeypatch.setattr("auditgraph.neo4j.sync.ping_connection", lambda driver, db: None)

    first = sync_neo4j(tmp_path, config, dry_run=False)
    second = sync_neo4j(tmp_path, config, dry_run=False)

    assert first.nodes_processed == second.nodes_processed == 2
    assert first.relationships_processed == second.relationships_processed == 1
    assert len(store["nodes"]) == 2
    assert len(store["relationships"]) == 1
