from __future__ import annotations

from pathlib import Path

from auditgraph.normalize.paths import normalize_path
from auditgraph.storage.hashing import sha256_file
from auditgraph.storage.manifests import IngestRecord
from auditgraph.storage.ontology import canonical_key, resolve_type


_ALLOWED_PARSE_STATUS = ("ok", "failed", "skipped")
_ALLOWED_SOURCE_ORIGIN = ("fresh", "cached")


def build_source_record(
    path: Path,
    root: Path,
    parser_id: str,
    parse_status: str,
    status_reason: str | None = None,
    skip_reason: str | None = None,
    extra_metadata: dict[str, object] | None = None,
    *,
    source_origin: str = "fresh",
) -> tuple[IngestRecord, dict[str, object]]:
    # Spec-028 Invariant I6: guard impossible combinations at the producer.
    # parse_status ∈ {ok, failed, skipped}; source_origin ∈ {fresh, cached};
    # source_origin="cached" implies parse_status="ok" (the cache only
    # stores successful parses — failed and skipped never populate it).
    if parse_status not in _ALLOWED_PARSE_STATUS:
        raise ValueError(
            f"parse_status must be one of {_ALLOWED_PARSE_STATUS}; got {parse_status!r}"
        )
    if source_origin not in _ALLOWED_SOURCE_ORIGIN:
        raise ValueError(
            f"source_origin must be one of {_ALLOWED_SOURCE_ORIGIN}; got {source_origin!r}"
        )
    if source_origin == "cached" and parse_status != "ok":
        raise ValueError(
            f"Invariant I6 violation: source_origin='cached' requires parse_status='ok'; "
            f"got parse_status={parse_status!r}. The cache never stores failed or "
            f"genuinely-skipped records — those are always fresh."
        )
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
        status_reason=status_reason,
        skip_reason=skip_reason,
        source_origin=source_origin,
    )
    metadata = {
        "path": normalized,
        "source_hash": source_hash,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "parser_id": parser_id,
        "parse_status": parse_status,
        "status_reason": status_reason,
        "skip_reason": skip_reason,
        "source_origin": source_origin,
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
