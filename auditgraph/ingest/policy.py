from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".log"}
PARSER_BY_SUFFIX = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".log": "text/plain",
}
SKIP_REASON_UNSUPPORTED = "unsupported_extension"


@dataclass(frozen=True)
class IngestionPolicy:
    allowed_extensions: set[str]


def load_policy(profile: dict) -> IngestionPolicy:
    raw = profile.get("ingestion", {})
    allowed = set(raw.get("allowed_extensions", [])) or set(DEFAULT_ALLOWED_EXTENSIONS)
    return IngestionPolicy(allowed_extensions=allowed)


def is_allowed(path: Path, policy: IngestionPolicy) -> bool:
    return path.suffix.lower() in policy.allowed_extensions


def split_by_allowlist(paths: Iterable[Path], policy: IngestionPolicy) -> tuple[list[Path], list[Path]]:
    allowed: list[Path] = []
    skipped: list[Path] = []
    for path in paths:
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return allowed, skipped


def parser_id_for(path: Path) -> str:
    return PARSER_BY_SUFFIX.get(path.suffix.lower(), "text/unknown")
