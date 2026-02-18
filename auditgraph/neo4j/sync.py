from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from auditgraph.config import Config
from auditgraph.neo4j.connection import create_driver, load_connection_from_env, map_neo4j_exception, ping_connection
from auditgraph.neo4j.cypher_builder import batch_records, generate_constraint_statements
from auditgraph.neo4j.export import ExportSummary
from auditgraph.neo4j.records import GraphNodeRecord, GraphRelationshipRecord, load_graph_nodes, load_graph_relationships
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.utils.redaction import build_redactor


def _node_props(record: GraphNodeRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": record.name,
        "type": record.type,
    }
    if record.canonical_key is not None:
        payload["canonical_key"] = record.canonical_key
    if record.profile is not None:
        payload["profile"] = record.profile
    if record.run_id is not None:
        payload["run_id"] = record.run_id
    if record.source_path is not None:
        payload["source_path"] = record.source_path
    if record.source_hash is not None:
        payload["source_hash"] = record.source_hash
    return payload


def _relationship_props(record: GraphRelationshipRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "type": record.type,
        "rule_id": record.rule_id,
    }
    if record.confidence is not None:
        payload["confidence"] = record.confidence
    if record.authority is not None:
        payload["authority"] = record.authority
    if record.evidence is not None:
        payload["evidence"] = record.evidence
    return payload


def ensure_constraints(session: Any, labels: set[str]) -> None:
    for statement in generate_constraint_statements(labels):
        session.run(statement)


def sync_nodes_batch(tx: Any, batch: list[GraphNodeRecord], dry_run: bool = False) -> tuple[int, int]:
    if dry_run:
        return (0, 0)
    updated = 0
    for item in batch:
        label = item.neo4j_label.lstrip(":")
        tx.run(
            f"MERGE (n:{label} {{id: $id}}) SET n += $props",
            id=item.id,
            props=_node_props(item),
        )
        updated += 1
    return (0, updated)


def sync_relationships_batch(
    tx: Any,
    batch: list[GraphRelationshipRecord],
    dry_run: bool = False,
) -> tuple[int, int]:
    if dry_run:
        return (0, 0)
    updated = 0
    for item in batch:
        tx.run(
            "MATCH (a {id: $from_id}), (b {id: $to_id}) "
            "MERGE (a)-[r:RELATES_TO {id: $id}]->(b) "
            "SET r += $props",
            from_id=item.from_id,
            to_id=item.to_id,
            id=item.id,
            props=_relationship_props(item),
        )
        updated += 1
    return (0, updated)


def sync_neo4j(root, config: Config, dry_run: bool = False) -> ExportSummary:
    started = perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    profile_name = config.active_profile()
    pkg_root = profile_pkg_root(root, config)
    redactor = build_redactor(root, config)

    nodes = load_graph_nodes(pkg_root, redactor=redactor)
    relationships, skipped = load_graph_relationships(
        pkg_root,
        node_ids={item.id for item in nodes},
        redactor=redactor,
    )

    conn = load_connection_from_env()
    summary = ExportSummary(
        mode="dry-run" if dry_run else "sync",
        profile=profile_name,
        timestamp=timestamp,
        target_uri=conn.uri,
        nodes_processed=len(nodes),
        relationships_processed=len(relationships),
        skipped_count=skipped,
    )

    try:
        driver = create_driver(conn)
        with driver:
            ping_connection(driver, conn.database)
            if dry_run:
                summary.duration_seconds = round(perf_counter() - started, 6)
                return summary

            labels = {item.neo4j_label for item in nodes}
            with driver.session(database=conn.database) as session:
                ensure_constraints(session, labels)

                for batch in batch_records(nodes, batch_size=1000):
                    created, updated = session.execute_write(sync_nodes_batch, batch, False)
                    summary.nodes_created += created
                    summary.nodes_updated += updated

                for batch in batch_records(relationships, batch_size=1000):
                    created, updated = session.execute_write(sync_relationships_batch, batch, False)
                    summary.relationships_created += created
                    summary.relationships_updated += updated
    except Exception as exc:
        summary.failed_count += 1
        summary.errors.append({"message": map_neo4j_exception(exc)})
        summary.duration_seconds = round(perf_counter() - started, 6)
        raise RuntimeError(summary.errors[-1]["message"]) from exc

    summary.duration_seconds = round(perf_counter() - started, 6)
    return summary
