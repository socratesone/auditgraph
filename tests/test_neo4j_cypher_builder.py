from __future__ import annotations

from auditgraph.neo4j.cypher_builder import (
    batch_records,
    generate_constraint_statements,
    generate_export_header,
    generate_node_merge_statement,
    generate_relationship_merge_statement,
)
from auditgraph.neo4j.records import GraphNodeRecord, GraphRelationshipRecord


def test_generate_export_header_contains_metadata() -> None:
    header = generate_export_header("default", "2026-02-17T00:00:00Z", 2, 1)
    assert "Profile: default" in header
    assert "Nodes: 2" in header
    assert "Relationships: 1" in header


def test_generate_constraint_statements_sorted_unique() -> None:
    statements = generate_constraint_statements([":AuditgraphTask", ":AuditgraphNote", ":AuditgraphTask"])
    assert len(statements) == 2
    assert ":AuditgraphNote" in statements[0]


def test_generate_merge_statements() -> None:
    node = GraphNodeRecord(
        id="ent_1",
        type="note",
        neo4j_label=":AuditgraphNote",
        name="My Note",
        canonical_key="note:1",
        profile="default",
    )
    rel = GraphRelationshipRecord(
        id="lnk_1",
        from_id="ent_1",
        to_id="ent_2",
        type="mentions",
        rule_id="rule.v1",
    )
    node_stmt = generate_node_merge_statement(node)
    rel_stmt = generate_relationship_merge_statement(rel)
    assert node_stmt.startswith("MERGE (n:AuditgraphNote")
    assert "SET n.name" in node_stmt
    assert "MERGE (a)-[r:RELATES_TO" in rel_stmt


def test_batch_records() -> None:
    batches = list(batch_records([1, 2, 3, 4, 5], batch_size=2))
    assert batches == [[1, 2], [3, 4], [5]]
