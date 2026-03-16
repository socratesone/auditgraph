from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from auditgraph.extract.document_types import DocumentExtraction
from auditgraph.ingest.policy import FAIL_REASON_CORRUPT, FAIL_REASON_OVERSIZED
from auditgraph.utils.document_text import normalize_document_text


def _extract_docx_fallback(path: Path) -> list[str] | None:
    if not zipfile.is_zipfile(path):
        return None
    with zipfile.ZipFile(path, "r") as archive:
        if "word/document.xml" not in archive.namelist():
            return None
        payload = archive.read("word/document.xml").decode("utf-8", errors="ignore")

    try:
        root = ET.fromstring(payload)
    except Exception:
        return None

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [
            (node.text or "")
            for node in paragraph.findall(".//w:t", namespace)
            if (node.text or "").strip()
        ]
        text = normalize_document_text("".join(parts))
        if text:
            paragraphs.append(text)
    return paragraphs


def extract_docx(path: Path, *, max_file_size_bytes: int | None = None) -> DocumentExtraction:
    if max_file_size_bytes is not None and path.stat().st_size > max_file_size_bytes:
        return DocumentExtraction(
            extractor_id="docx/python-docx",
            extractor_version="day1",
            status="failed",
            status_reason=FAIL_REASON_OVERSIZED,
            text="",
        )

    segments: list[dict[str, object]] = []
    ordered: list[str] = []
    parsed = False
    try:
        from docx import Document  # type: ignore

        document = Document(str(path))
        for index, paragraph in enumerate(document.paragraphs):
            normalized = normalize_document_text(paragraph.text)
            if not normalized:
                continue
            ordered.append(normalized)
            segments.append(
                {
                    "order": len(segments),
                    "type": "paragraph",
                    "text": normalized,
                    "page_start": None,
                    "page_end": None,
                    "paragraph_index": index,
                }
            )
        parsed = True
    except Exception:
        parsed = False

    if not parsed or not ordered:
        fallback = _extract_docx_fallback(path)
        if fallback is None:
            return DocumentExtraction(
                extractor_id="docx/python-docx",
                extractor_version="day1",
                status="failed",
                status_reason=FAIL_REASON_CORRUPT,
                text="",
            )
        for index, paragraph in enumerate(fallback):
            ordered.append(paragraph)
            segments.append(
                {
                    "order": len(segments),
                    "type": "paragraph",
                    "text": paragraph,
                    "page_start": None,
                    "page_end": None,
                    "paragraph_index": index,
                }
            )

    if not ordered:
        return DocumentExtraction(
            extractor_id="docx/python-docx",
            extractor_version="day1",
            status="failed",
            status_reason=FAIL_REASON_CORRUPT,
            text="",
        )

    return DocumentExtraction(
        extractor_id="docx/python-docx",
        extractor_version="day1",
        status="ok",
        status_reason=None,
        text="\n\n".join(ordered),
        segments=segments,
        metadata={},
    )
