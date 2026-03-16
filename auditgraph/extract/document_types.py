from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SegmentRecord:
    segment_id: str
    document_id: str
    order: int
    type: str
    text: str
    page_start: int | None = None
    page_end: int | None = None
    paragraph_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    order: int
    text: str
    token_count: int
    segment_ids: list[str] = field(default_factory=list)
    overlap_tokens: int = 0
    source_path: str = ""
    source_hash: str = ""
    page_start: int | None = None
    page_end: int | None = None
    paragraph_index_start: int | None = None
    paragraph_index_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentExtraction:
    extractor_id: str
    extractor_version: str
    status: str
    status_reason: str | None
    text: str
    segments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
