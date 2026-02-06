from __future__ import annotations

from pathlib import Path

from auditgraph.normalize.paths import normalize_path
from auditgraph.storage.hashing import sha256_file
from auditgraph.storage.manifests import IngestRecord
from auditgraph.storage.ontology import canonical_key, resolve_type


def build_source_record(
    path: Path,
    root: Path,
    parser_id: str,
    parse_status: str,
    skip_reason: str | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[IngestRecord, dict[str, object]]:
    stat = path.stat()
    source_hash = sha256_file(path)
    normalized = normalize_path(path, root=root)
    record = IngestRecord(
        path=normalized,
        source_hash=source_hash,
        size=stat.st_size,
        mtime=stat.st_mtime,
        parser_id=parser_id,
        parse_status=parse_status,
        skip_reason=skip_reason,
    )
    metadata = {
        "path": normalized,
        "source_hash": source_hash,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "parser_id": parser_id,
        "parse_status": parse_status,
        "skip_reason": skip_reason,
    }
    frontmatter = None
    if extra_metadata:
        frontmatter = extra_metadata.get("frontmatter")
    if isinstance(frontmatter, dict):
        title = str(frontmatter.get("title", path.stem))
        entity_type = resolve_type({"type": "note"}, primary="ag", allow_secondary=True)
        metadata["knowledge_model"] = {
            "type": entity_type,
            "canonical_key": canonical_key(title),
        }
    if extra_metadata:
        metadata.update(extra_metadata)
    return record, metadata
