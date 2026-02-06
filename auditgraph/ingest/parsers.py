from __future__ import annotations

from pathlib import Path


def parse_file(path: Path) -> tuple[str, str, str]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        parser_id = "text/markdown"
    elif suffix in {".txt", ".log"}:
        parser_id = "text/plain"
    else:
        parser_id = "text/unknown"

    text = path.read_text(encoding="utf-8", errors="replace")
    return parser_id, "ok", text
