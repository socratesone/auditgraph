from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditgraph.storage.artifacts import read_json
from auditgraph.utils.redaction import Redactor


@dataclass(frozen=True)
class GraphNodeRecord:
    id: str
    type: str
    neo4j_label: str
    name: str
    canonical_key: str | None = None
    profile: str | None = None
    run_id: str | None = None
    source_path: str | None = None
    source_hash: str | None = None


@dataclass(frozen=True)
class GraphRelationshipRecord:
    id: str
    from_id: str
    to_id: str
    type: str
    rule_id: str
    confidence: float | None = None
    authority: str | None = None
    evidence: list[dict[str, Any]] | None = None


def map_entity_type_to_label(entity_type: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", " ", entity_type).strip()
    if not token:
        token = "entity"
    parts = token.split()
    pascal = "".join(part[:1].upper() + part[1:] for part in parts)
    return f":Auditgraph{pascal}"


def _iter_json_files(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return sorted(base_dir.rglob("*.json"), key=lambda path: str(path))


def _extract_source(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    refs = payload.get("refs")
    if isinstance(refs, list) and refs:
        first = refs[0]
        if isinstance(first, dict):
            return (
                str(first.get("source_path", "")) or None,
                str(first.get("source_hash", "")) or None,
            )
    return None, None


def load_graph_nodes(pkg_root: Path, redactor: Redactor | None = None) -> list[GraphNodeRecord]:
    profile = pkg_root.name
    records: list[GraphNodeRecord] = []
    for path in _iter_json_files(pkg_root / "entities"):
        payload = read_json(path)
        if redactor is not None:
            payload = redactor.redact_payload(payload).value
        if not isinstance(payload, dict):
            continue
        entity_id = str(payload.get("id", ""))
        entity_type = str(payload.get("type", "entity"))
        name = str(payload.get("name", ""))
        if not entity_id or not name:
            continue
        provenance = payload.get("provenance")
        run_id = None
        if isinstance(provenance, dict):
            run_id = str(provenance.get("run_id", "")) or None
        source_path, source_hash = _extract_source(payload)
        records.append(
            GraphNodeRecord(
                id=entity_id,
                type=entity_type,
                neo4j_label=map_entity_type_to_label(entity_type),
                name=name,
                canonical_key=str(payload.get("canonical_key", "")) or None,
                profile=profile,
                run_id=run_id,
                source_path=source_path,
                source_hash=source_hash,
            )
        )
    records.sort(key=lambda item: item.id)
    return records


def load_graph_relationships(
    pkg_root: Path,
    node_ids: set[str] | None = None,
    redactor: Redactor | None = None,
) -> tuple[list[GraphRelationshipRecord], int]:
    records: list[GraphRelationshipRecord] = []
    skipped = 0
    for path in _iter_json_files(pkg_root / "links"):
        payload = read_json(path)
        if redactor is not None:
            payload = redactor.redact_payload(payload).value
        if not isinstance(payload, dict):
            skipped += 1
            continue
        link_id = str(payload.get("id", ""))
        from_id = str(payload.get("from_id", ""))
        to_id = str(payload.get("to_id", ""))
        if not link_id or not from_id or not to_id:
            skipped += 1
            continue
        if node_ids is not None and (from_id not in node_ids or to_id not in node_ids):
            skipped += 1
            continue
        evidence = payload.get("evidence")
        evidence_value: list[dict[str, Any]] | None = None
        if isinstance(evidence, list):
            evidence_value = [item for item in evidence if isinstance(item, dict)]
        confidence = payload.get("confidence")
        confidence_value = float(confidence) if isinstance(confidence, (int, float)) else None
        records.append(
            GraphRelationshipRecord(
                id=link_id,
                from_id=from_id,
                to_id=to_id,
                type=str(payload.get("type", "relates_to")),
                rule_id=str(payload.get("rule_id", "")),
                confidence=confidence_value,
                authority=str(payload.get("authority", "")) or None,
                evidence=evidence_value,
            )
        )
    records.sort(key=lambda item: (item.from_id, item.to_id, item.id))
    return records, skipped
