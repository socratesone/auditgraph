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
            "skip_reason": record.skip_reason,
        }
        for record in sorted(records, key=lambda item: item.path)
    ]
    return sha256_text(json.dumps(payload, sort_keys=True))


def deterministic_run_id(input_hash: str, config_hash: str) -> str:
    return f"run_{sha256_text(input_hash + config_hash)}"
