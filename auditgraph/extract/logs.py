from __future__ import annotations

from pathlib import Path


def extract_log_signatures(path: Path) -> list[dict[str, object]]:
    if path.suffix.lower() not in {".log", ".txt"}:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    signatures: list[dict[str, object]] = []
    for line in text.splitlines():
        if "error" in line.lower():
            signatures.append({"signature": line.strip(), "source_path": path.as_posix()})
    return signatures
