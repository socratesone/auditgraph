from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from auditgraph.storage.manifests import IngestRecord


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, encoding: str = "utf-8") -> str:
    return sha256_bytes(text.encode(encoding))


def sha256_json(payload: object) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def inputs_hash(records: Iterable[IngestRecord]) -> str:
    payload = [record.source_hash for record in records]
    return sha256_text(":".join(sorted(payload)))


def outputs_hash(records: Iterable[IngestRecord]) -> str:
    payload = [
        {
            "path": record.path,
            "source_hash": record.source_hash,
            "parse_status": record.parse_status,
            "status_reason": record.status_reason,
            "skip_reason": record.skip_reason,
        }
        for record in sorted(records, key=lambda item: item.path)
    ]
    return sha256_text(json.dumps(payload, sort_keys=True))


def deterministic_run_id(input_hash: str, config_hash: str) -> str:
    return f"run_{sha256_text(input_hash + config_hash)}"


def deterministic_document_id(source_path: str, source_hash: str = "") -> str:
    return f"doc_{sha256_text(source_path)[:24]}"


def deterministic_segment_id(document_id: str, segment_type: str, order: int, text: str) -> str:
    return f"seg_{sha256_text(f'{document_id}:{segment_type}:{order}:{text}')[:24]}"


def deterministic_chunk_id(document_id: str, order: int, text: str) -> str:
    return f"chk_{sha256_text(f'{document_id}:{order}:{text}')[:24]}"


def deterministic_timestamp(seed: str) -> str:
    """Derive a stable ISO-8601 timestamp from a seed string.

    Uses first 8 hex chars of SHA-256 as seconds since epoch,
    modulo 10^9 (~31 years) to keep the result in a reasonable range.
    """
    from datetime import datetime, timezone

    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    seconds = int(digest[:8], 16) % (10**9)
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
