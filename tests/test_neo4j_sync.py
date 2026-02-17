from __future__ import annotations

from pathlib import Path
from typing import Any

from auditgraph.config import load_config
from auditgraph.neo4j.sync import sync_neo4j
from auditgraph.storage.artifacts import profile_pkg_root
from tests.fixtures.neo4j_fixtures import write_test_graph


class _FakeTx:
    def __init__(self, store: dict[str, set[str]]) -> None:
        self._store = store

    def run(self, query: str, **params: object) -> None:
        if "MERGE (n:" in query and "id" in params:
            self._store["nodes"].add(str(params["id"]))
        if "RELATES_TO" in query and "id" in params:
            self._store["relationships"].add(str(params["id"]))


class _FakeSession:
    def __init__(self, store: dict[str, set[str]]) -> None:
        self._store = store
        self.constraint_calls = 0

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def run(self, query: str, **params: object) -> None:
        if query.startswith("CREATE CONSTRAINT"):
            self.constraint_calls += 1

    def execute_write(self, fn, batch, dry_run):
        tx = _FakeTx(self._store)
        return fn(tx, batch, dry_run)


class _FakeDriver:
    def __init__(self, store: dict[str, set[str]]) -> None:
        self._store = store

    def __enter__(self) -> "_FakeDriver":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def session(self, database: str):
        return _FakeSession(self._store)


def test_sync_neo4j_dry_run_no_mutation(tmp_path: Path, monkeypatch) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)
    store = {"nodes": set(), "relationships": set()}

    monkeypatch.setattr(
        "auditgraph.neo4j.sync.load_connection_from_env",
        lambda: type("Conn", (), {"uri": "bolt://x", "database": "neo4j"})(),
    )
    monkeypatch.setattr("auditgraph.neo4j.sync.create_driver", lambda conn: _FakeDriver(store))
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
        lambda: type("Conn", (), {"uri": "bolt://x", "database": "neo4j"})(),
    )
    monkeypatch.setattr("auditgraph.neo4j.sync.create_driver", lambda conn: _FakeDriver(store))
    monkeypatch.setattr("auditgraph.neo4j.sync.ping_connection", lambda driver, db: None)

    first = sync_neo4j(tmp_path, config, dry_run=False)
    second = sync_neo4j(tmp_path, config, dry_run=False)

    assert first.nodes_processed == second.nodes_processed == 2
    assert first.relationships_processed == second.relationships_processed == 1
    assert len(store["nodes"]) == 2
    assert len(store["relationships"]) == 1
