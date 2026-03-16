from __future__ import annotations

from pathlib import Path
import re

from auditgraph.extract.document_types import DocumentExtraction
from auditgraph.ingest.policy import (
    FAIL_REASON_CORRUPT,
    FAIL_REASON_ENCRYPTED,
    FAIL_REASON_OCR_REQUIRED,
    FAIL_REASON_OCR_UNAVAILABLE,
    FAIL_REASON_OVERSIZED,
)
from auditgraph.utils.document_text import normalize_document_text


def _extract_text_fallback(path: Path) -> list[str] | None:
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        return None
    decoded = data.decode("latin-1", errors="ignore")
    values = re.findall(r"\(([^\)]*)\)\s*Tj", decoded)
    pages = [normalize_document_text(value) for value in values if normalize_document_text(value)]
    return pages


def extract_pdf(path: Path, *, ocr_mode: str = "off", max_file_size_bytes: int | None = None) -> DocumentExtraction:
    if max_file_size_bytes is not None and path.stat().st_size > max_file_size_bytes:
        return DocumentExtraction(
            extractor_id="pdf/pypdf",
            extractor_version="day1",
            status="failed",
            status_reason=FAIL_REASON_OVERSIZED,
            text="",
        )

    page_texts: list[str] = []
    segments: list[dict[str, object]] = []

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False) and ocr_mode == "off":
            return DocumentExtraction(
                extractor_id="pdf/pypdf",
                extractor_version="day1",
                status="failed",
                status_reason=FAIL_REASON_ENCRYPTED,
                text="",
            )

        for index, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            normalized = normalize_document_text(extracted)
            if normalized:
                page_texts.append(normalized)
                segments.append(
                    {
                        "order": index - 1,
                        "type": "page",
                        "text": normalized,
                        "page_start": index,
                        "page_end": index,
                        "paragraph_index": None,
                    }
                )
    except Exception:
        fallback_pages = _extract_text_fallback(path)
        if fallback_pages is None:
            return DocumentExtraction(
                extractor_id="pdf/pypdf",
                extractor_version="day1",
                status="failed",
                status_reason=FAIL_REASON_CORRUPT,
                text="",
            )
        for index, normalized in enumerate(fallback_pages, start=1):
            page_texts.append(normalized)
            segments.append(
                {
                    "order": index - 1,
                    "type": "page",
                    "text": normalized,
                    "page_start": index,
                    "page_end": index,
                    "paragraph_index": None,
                }
            )

    if not page_texts:
        if ocr_mode == "off":
            return DocumentExtraction(
                extractor_id="pdf/pypdf",
                extractor_version="day1",
                status="failed",
                status_reason=FAIL_REASON_OCR_REQUIRED,
                text="",
            )
        return DocumentExtraction(
            extractor_id="pdf/pypdf",
            extractor_version="day1",
            status="failed",
            status_reason=FAIL_REASON_OCR_UNAVAILABLE,
            text="",
            metadata={"ocr_mode": ocr_mode, "ocr_applied": False},
        )

    return DocumentExtraction(
        extractor_id="pdf/pypdf",
        extractor_version="day1",
        status="ok",
        status_reason=None,
        text="\n\n".join(page_texts),
        segments=segments,
        metadata={"ocr_mode": ocr_mode, "ocr_applied": ocr_mode == "on"},
    )
