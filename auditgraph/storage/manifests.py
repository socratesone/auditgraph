from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class IngestRecord:
    path: str
    source_hash: str
    size: int
    mtime: float
    parser_id: str
    parse_status: str
    skip_reason: str | None = None


@dataclass(frozen=True)
class IngestManifest:
    run_id: str
    started_at: str
    pipeline_version: str
    config_hash: str
    inputs_hash: str
    outputs_hash: str
    records: list[IngestRecord] = field(default_factory=list)
    ingested_count: int = 0
    skipped_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
