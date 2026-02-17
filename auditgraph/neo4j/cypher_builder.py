from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

from auditgraph.neo4j.records import GraphNodeRecord, GraphRelationshipRecord


def generate_export_header(
    profile: str,
    timestamp: str,
    node_count: int,
    relationship_count: int,
    format_version: str = "1.0.0",
) -> str:
    return "\n".join(
        [
            "// Neo4j Export from Auditgraph",
            f"// Profile: {profile}",
            f"// Timestamp: {timestamp}",
            f"// Nodes: {node_count}",
            f"// Relationships: {relationship_count}",
            f"// Format Version: {format_version}",
        ]
    )


def generate_constraint_statements(labels: Iterable[str]) -> list[str]:
    statements: list[str] = []
    normalized = sorted({label.lstrip(":") for label in labels if label})
    for label in normalized:
        key = label.replace("Auditgraph", "auditgraph_").replace("-", "_").lower()
        statements.append(
            f"CREATE CONSTRAINT {key}_id_unique IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
    return statements


def _literal(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def generate_node_merge_statement(record: GraphNodeRecord) -> str:
    label = record.neo4j_label.lstrip(":")
    props = {
        "name": record.name,
        "type": record.type,
        "canonical_key": record.canonical_key,
        "profile": record.profile,
        "run_id": record.run_id,
        "source_path": record.source_path,
        "source_hash": record.source_hash,
    }
    set_parts = [f"n.{key} = {_literal(value)}" for key, value in props.items() if value is not None]
    set_clause = ", ".join(set_parts)
    return f"MERGE (n:{label} {{id: {_literal(record.id)}}}) SET {set_clause};"


def generate_relationship_merge_statement(record: GraphRelationshipRecord) -> str:
    evidence = json.dumps(record.evidence, ensure_ascii=False) if record.evidence is not None else None
    props = {
        "type": record.type,
        "rule_id": record.rule_id,
        "confidence": record.confidence,
        "authority": record.authority,
        "evidence": evidence,
    }
    set_parts = [f"r.{key} = {_literal(value)}" for key, value in props.items() if value is not None]
    set_clause = ", ".join(set_parts)
    return (
        f"MATCH (a {{id: {_literal(record.from_id)}}}), (b {{id: {_literal(record.to_id)}}}) "
        f"MERGE (a)-[r:RELATES_TO {{id: {_literal(record.id)}}}]->(b) "
        f"SET {set_clause};"
    )


def batch_records(records: Iterable[object], batch_size: int = 1000) -> Iterator[list[object]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    current: list[object] = []
    for record in records:
        current.append(record)
        if len(current) >= batch_size:
            yield current
            current = []
    if current:
        yield current
