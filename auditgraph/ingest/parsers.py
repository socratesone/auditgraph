from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auditgraph.extract.docx_backend import extract_docx
from auditgraph.extract.pdf_backend import extract_pdf
from auditgraph.ingest.frontmatter import extract_frontmatter
from auditgraph.ingest.policy import (
    FAIL_REASON_UNSUPPORTED_DOC,
    SKIP_REASON_UNSUPPORTED,
    IngestionPolicy,
    is_allowed,
    parser_id_for,
)
from auditgraph.storage.hashing import (
    deterministic_chunk_id,
    deterministic_document_id,
    deterministic_segment_id,
)
from auditgraph.utils.chunking import chunk_text
from auditgraph.utils.document_text import normalize_document_text
from auditgraph.utils.redaction import Redactor


@dataclass(frozen=True)
class ParseResult:
    parser_id: str
    status: str
    text: str
    status_reason: str | None = None
    skip_reason: str | None = None
    metadata: dict[str, object] | None = None


def _default_ingest_options() -> dict[str, object]:
    return {
        "ocr_mode": "off",
        "chunk_tokens": 200,
        "chunk_overlap_tokens": 40,
        "max_file_size_bytes": 209715200,
        "ingest_config_hash": "",
        "source_hash": "",
    }


def _build_document_metadata(
    *,
    path: Path,
    source_hash: str,
    parser_id: str,
    text: str,
    extractor_id: str,
    extractor_version: str,
    segments: list[dict[str, object]],
    options: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    # Spec 027 FR-016: redact full document text BEFORE chunking so multi-line
    # secrets (PEM keys) are caught regardless of chunk boundaries. The hotfix
    # (Spec 026 C1) redacted post-chunking, which was too late for cross-chunk
    # secrets. See specs/027-security-hardening/spec.md US5.
    redactor = options.get("redactor")
    if not isinstance(redactor, Redactor):
        raise ValueError(
            "parse_options[\"redactor\"] is required; parser-entry redaction is "
            "the single canonical redaction site per Spec 027 FR-016"
        )
    text = redactor.redact_text(text).value
    document_id = deterministic_document_id(path.as_posix(), source_hash)
    normalized_segments: list[dict[str, object]] = []
    for segment in sorted(segments, key=lambda item: int(item.get("order", 0))):
        order = int(segment.get("order", 0))
        segment_text = normalize_document_text(str(segment.get("text", "")))
        segment_text = redactor.redact_text(segment_text).value
        segment_type = str(segment.get("type", "other"))
        if not segment_text:
            continue
        normalized_segments.append(
            {
                "segment_id": deterministic_segment_id(document_id, segment_type, order, segment_text),
                "document_id": document_id,
                "order": order,
                "type": segment_type,
                "text": segment_text,
                "page_start": segment.get("page_start"),
                "page_end": segment.get("page_end"),
                "paragraph_index": segment.get("paragraph_index"),
            }
        )

    chunk_size = int(options.get("chunk_tokens", 200))
    overlap = int(options.get("chunk_overlap_tokens", 40))
    chunks = chunk_text(text, chunk_size, overlap)
    chunk_records: list[dict[str, object]] = []
    for index, chunk in enumerate(chunks):
        page_values = [seg.get("page_start") for seg in normalized_segments if isinstance(seg.get("page_start"), int)]
        page_end_values = [seg.get("page_end") for seg in normalized_segments if isinstance(seg.get("page_end"), int)]
        paragraph_values = [
            seg.get("paragraph_index")
            for seg in normalized_segments
            if isinstance(seg.get("paragraph_index"), int)
        ]
        chunk_records.append(
            {
                "chunk_id": deterministic_chunk_id(document_id, index, str(chunk.get("text", ""))),
                "document_id": document_id,
                "order": index,
                "text": str(chunk.get("text", "")),
                "token_count": int(chunk.get("token_count", 0)),
                "segment_ids": [seg["segment_id"] for seg in normalized_segments],
                "overlap_tokens": int(chunk.get("overlap_tokens", 0)),
                "source_path": path.as_posix(),
                "source_hash": source_hash,
                "page_start": min(page_values) if page_values else None,
                "page_end": max(page_end_values) if page_end_values else None,
                "paragraph_index_start": min(paragraph_values) if paragraph_values else None,
                "paragraph_index_end": max(paragraph_values) if paragraph_values else None,
            }
        )

    payload: dict[str, object] = {
        "document": {
            "document_id": document_id,
            "source_path": path.as_posix(),
            "source_hash": source_hash,
            "mime_type": parser_id,
            "file_size": path.stat().st_size,
            "extractor_id": extractor_id,
            "extractor_version": extractor_version,
            "ingest_config_hash": str(options.get("ingest_config_hash", "")),
            "status": "ok",
            "status_reason": None,
            "hash_history": [source_hash],
        },
        "segments": normalized_segments,
        "chunks": chunk_records,
    }
    if extra:
        payload.update(extra)
    return payload


def parse_file(path: Path, policy: IngestionPolicy, ingest_options: dict[str, object] | None = None) -> ParseResult:
    # Spec 027 FR-016: parser-entry is the single canonical redaction site.
    # A missing redactor MUST raise loudly rather than silently skip scrubbing
    # (that silent-skip path is exactly what Spec 026 C1 closed).
    if not ingest_options or not isinstance(ingest_options.get("redactor"), Redactor):
        raise ValueError(
            "parse_options[\"redactor\"] is required; parser-entry redaction is "
            "the single canonical redaction site per Spec 027 FR-016"
        )
    options = _default_ingest_options()
    options.update(ingest_options)

    suffix = path.suffix.lower()
    if suffix == ".doc":
        return ParseResult(
            parser_id="document/doc",
            status="failed",
            text="",
            status_reason=FAIL_REASON_UNSUPPORTED_DOC,
            skip_reason=FAIL_REASON_UNSUPPORTED_DOC,
        )

    if not is_allowed(path, policy):
        return ParseResult(
            parser_id="text/unknown",
            status="skipped",
            text="",
            status_reason=SKIP_REASON_UNSUPPORTED,
            skip_reason=SKIP_REASON_UNSUPPORTED,
        )

    parser_id = parser_id_for(path)
    source_hash = str(options.get("source_hash", ""))
    if not source_hash:
        try:
            from auditgraph.storage.hashing import sha256_file

            source_hash = sha256_file(path)
        except Exception:
            source_hash = ""

    if parser_id == "document/pdf":
        result = extract_pdf(
            path,
            ocr_mode=str(options.get("ocr_mode", "off")),
            max_file_size_bytes=int(options.get("max_file_size_bytes", 209715200)),
        )
        if result.status != "ok":
            return ParseResult(
                parser_id=parser_id,
                status=result.status,
                text="",
                status_reason=result.status_reason,
                skip_reason=result.status_reason,
                metadata={"ocr_mode": options.get("ocr_mode", "off"), **result.metadata},
            )
        text = normalize_document_text(result.text)
        metadata = _build_document_metadata(
            path=path,
            source_hash=source_hash,
            parser_id=parser_id,
            text=text,
            extractor_id=result.extractor_id,
            extractor_version=result.extractor_version,
            segments=result.segments,
            options=options,
            extra=result.metadata,
        )
        return ParseResult(parser_id=parser_id, status="ok", text=text, metadata=metadata)

    if parser_id == "document/docx":
        result = extract_docx(path, max_file_size_bytes=int(options.get("max_file_size_bytes", 209715200)))
        if result.status != "ok":
            return ParseResult(
                parser_id=parser_id,
                status=result.status,
                text="",
                status_reason=result.status_reason,
                skip_reason=result.status_reason,
            )
        text = normalize_document_text(result.text)
        metadata = _build_document_metadata(
            path=path,
            source_hash=source_hash,
            parser_id=parser_id,
            text=text,
            extractor_id=result.extractor_id,
            extractor_version=result.extractor_version,
            segments=result.segments,
            options=options,
            extra=result.metadata,
        )
        return ParseResult(parser_id=parser_id, status="ok", text=text, metadata=metadata)

    text = path.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, object] = {}
    if parser_id == "text/markdown":
        metadata["frontmatter"] = extract_frontmatter(text)

    if parser_id in ("text/plain", "text/markdown"):
        normalized = normalize_document_text(text)
        if normalized:
            metadata = _build_document_metadata(
                path=path,
                source_hash=source_hash,
                parser_id=parser_id,
                text=normalized,
                extractor_id="text_plain_parser",
                extractor_version="v1",
                segments=[],
                options=options,
                extra=metadata,
            )

    return ParseResult(parser_id=parser_id, status="ok", text=text, metadata=metadata)
