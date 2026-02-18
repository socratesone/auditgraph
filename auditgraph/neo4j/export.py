from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from auditgraph.config import Config
from auditgraph.neo4j.cypher_builder import (
    batch_records,
    generate_constraint_statements,
    generate_export_header,
    generate_node_merge_statement,
    generate_relationship_merge_statement,
)
from auditgraph.neo4j.records import GraphNodeRecord, GraphRelationshipRecord, load_graph_nodes, load_graph_relationships
from auditgraph.storage.artifacts import ensure_dir, profile_pkg_root
from auditgraph.utils.redaction import build_redactor


@dataclass
class ExportSummary:
    mode: str
    profile: str
    timestamp: str
    output_path: str | None = None
    target_uri: str | None = None
    nodes_processed: int = 0
    relationships_processed: int = 0
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    duration_seconds: float = 0.0
    errors: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _default_output_path(root: Path, profile: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "exports" / "neo4j" / f"{profile}-{timestamp}.cypher"


def write_batched_cypher_file(
    nodes: list[GraphNodeRecord],
    relationships: list[GraphRelationshipRecord],
    output_path: Path,
    profile: str,
    timestamp: str,
) -> None:
    ensure_dir(output_path.parent)
    labels = {item.neo4j_label for item in nodes}
    lines: list[str] = [generate_export_header(profile, timestamp, len(nodes), len(relationships)), ""]
    lines.append("// === Constraints ===")
    lines.extend(generate_constraint_statements(labels))
    lines.append("")

    node_batches = list(batch_records(nodes, batch_size=1000))
    for index, batch in enumerate(node_batches, start=1):
        lines.append(f"// === Nodes (Batch {index} of {len(node_batches)}) ===")
        lines.append(":begin")
        lines.extend(generate_node_merge_statement(item) for item in batch)
        lines.append(":commit")
        lines.append("")

    rel_batches = list(batch_records(relationships, batch_size=1000))
    for index, batch in enumerate(rel_batches, start=1):
        lines.append(f"// === Relationships (Batch {index} of {len(rel_batches)}) ===")
        lines.append(":begin")
        lines.extend(generate_relationship_merge_statement(item) for item in batch)
        lines.append(":commit")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_neo4j(root: Path, config: Config, output_path: Path | None = None) -> ExportSummary:
    started = perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    profile = config.active_profile()
    pkg_root = profile_pkg_root(root, config)
    redactor = build_redactor(root, config)

    nodes = load_graph_nodes(pkg_root, redactor=redactor)
    relationships, skipped = load_graph_relationships(
        pkg_root,
        node_ids={item.id for item in nodes},
        redactor=redactor,
    )
    resolved_output = output_path or _default_output_path(root, profile)

    write_batched_cypher_file(nodes, relationships, resolved_output, profile, timestamp)

    elapsed = perf_counter() - started
    return ExportSummary(
        mode="export",
        profile=profile,
        timestamp=timestamp,
        output_path=str(resolved_output),
        nodes_processed=len(nodes),
        relationships_processed=len(relationships),
        skipped_count=skipped,
        failed_count=0,
        duration_seconds=round(elapsed, 6),
    )
