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
    status_reason: str | None = None
    skip_reason: str | None = None
    # Spec-028 FR-001/FR-002: execution origin is orthogonal to parse outcome.
    # "fresh" = parsed during this run; "cached" = cache hit on source_hash.
    # Downstream stages filter on parse_status alone; source_origin is
    # observability-only.
    source_origin: str = "fresh"


@dataclass(frozen=True)
class IngestManifest:
    version: str
    schema_version: str
    stage: str
    run_id: str
    started_at: str
    finished_at: str
    pipeline_version: str
    config_hash: str
    inputs_hash: str
    outputs_hash: str
    status: str
    artifacts: list[str] = field(default_factory=list)
    records: list[IngestRecord] = field(default_factory=list)
    ingested_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    # Spec-028 FR-018: persisted manifest always serializes `warnings`
    # as a list (even `[]`) — operators can rely on the stable JSON path.
    warnings: list[dict[str, str]] = field(default_factory=list)
    # Spec-028 US6 (BUG-3 fix): wall-clock timestamps. Populated via
    # auditgraph.storage.hashing.wall_clock_now(). MUST NEVER participate
    # in outputs_hash; `started_at`/`finished_at` above remain deterministic.
    wall_clock_started_at: str | None = None
    wall_clock_finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageManifest:
    version: str
    schema_version: str
    stage: str
    run_id: str
    inputs_hash: str
    outputs_hash: str
    config_hash: str
    status: str
    started_at: str
    finished_at: str
    artifacts: list[str] = field(default_factory=list)
    # Spec-028 FR-018: see IngestManifest.warnings.
    warnings: list[dict[str, str]] = field(default_factory=list)
    # Spec-028 US6 (BUG-3 fix): see IngestManifest.wall_clock_started_at.
    wall_clock_started_at: str | None = None
    wall_clock_finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
