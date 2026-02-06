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


@dataclass(frozen=True)
class IngestManifest:
    run_id: str
    started_at: str
    records: list[IngestRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
