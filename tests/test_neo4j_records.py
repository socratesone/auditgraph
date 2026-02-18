from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.neo4j.records import load_graph_nodes, load_graph_relationships, map_entity_type_to_label
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.utils.redaction import build_redactor
from tests.fixtures.neo4j_fixtures import write_test_graph


def test_map_entity_type_to_label() -> None:
    assert map_entity_type_to_label("note") == ":AuditgraphNote"
    assert map_entity_type_to_label("project_task") == ":AuditgraphProjectTask"


def test_load_graph_nodes_sorted_and_redacted(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)

    redactor = build_redactor(tmp_path, config)
    nodes = load_graph_nodes(pkg_root, redactor=redactor)

    assert [node.id for node in nodes] == ["ent_aa01", "ent_bb01"]
    serialized = " ".join(node.name for node in nodes)
    assert "abc123" not in serialized


def test_load_graph_relationships_filters_missing_nodes(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)

    rels, skipped = load_graph_relationships(pkg_root, node_ids={"ent_aa01"}, redactor=None)
    assert rels == []
    assert skipped == 1
