from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_ALLOWED_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".pdf",
    ".docx",
}
PARSER_BY_SUFFIX = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".py": "text/code",
    ".js": "text/code",
    ".ts": "text/code",
    ".tsx": "text/code",
    ".jsx": "text/code",
    ".pdf": "document/pdf",
    ".docx": "document/docx",
    ".doc": "document/doc",
}
SKIP_REASON_UNSUPPORTED = "unsupported_extension"
SKIP_REASON_UNCHANGED = "unchanged_source_hash"
FAIL_REASON_UNSUPPORTED_DOC = "unsupported_doc_format"
FAIL_REASON_ENCRYPTED = "encrypted_pdf"
FAIL_REASON_CORRUPT = "corrupt_or_unreadable"
FAIL_REASON_OVERSIZED = "oversized_file"
FAIL_REASON_OCR_REQUIRED = "ocr_required"
FAIL_REASON_OCR_UNAVAILABLE = "ocr_engine_unavailable"


@dataclass(frozen=True)
class IngestionPolicy:
    allowed_extensions: set[str]


def load_policy(profile: dict) -> IngestionPolicy:
    raw = profile.get("ingestion", {})
    allowed = set(raw.get("allowed_extensions", [])) or set(DEFAULT_ALLOWED_EXTENSIONS)
    return IngestionPolicy(allowed_extensions=allowed)


def is_allowed(path: Path, policy: IngestionPolicy) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".doc":
        return True
    return suffix in policy.allowed_extensions


def matches_exclude(path: Path, root: Path, exclude_globs: Iterable[str]) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_globs)


def parser_id_for(path: Path) -> str:
    return PARSER_BY_SUFFIX.get(path.suffix.lower(), "text/unknown")
