from __future__ import annotations

import sys
from types import ModuleType

import pytest

from auditgraph.neo4j.connection import Neo4jConnectionProfile, create_driver, load_connection_from_env


def test_load_connection_from_env_success() -> None:
    profile = load_connection_from_env(
        {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "pass",
            "NEO4J_DATABASE": "neo4j",
        }
    )
    assert profile.uri == "bolt://localhost:7687"
    assert profile.user == "neo4j"


def test_load_connection_from_env_missing_var() -> None:
    with pytest.raises(ValueError):
        load_connection_from_env({"NEO4J_URI": "bolt://localhost:7687"})


def test_create_driver_uses_graphdatabase(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    class _GraphDatabase:
        @staticmethod
        def driver(uri, auth, max_connection_pool_size):
            called["uri"] = uri
            called["auth"] = auth
            called["pool"] = max_connection_pool_size
            return "driver"

    fake_module = ModuleType("neo4j")
    fake_module.GraphDatabase = _GraphDatabase
    monkeypatch.setitem(sys.modules, "neo4j", fake_module)

    profile = Neo4jConnectionProfile(uri="bolt://localhost:7687", user="neo4j", password="pw")
    driver = create_driver(profile)

    assert driver == "driver"
    assert called["uri"] == profile.uri
