from __future__ import annotations

from pathlib import Path


def normalize_path(path: Path | str, root: Path | None = None, style: str = "posix") -> str:
    raw = Path(path)
    if root is not None:
        try:
            raw = raw.resolve().relative_to(root.resolve())
        except Exception:
            raw = raw.resolve()
    if style == "posix":
        return raw.as_posix()
    return str(raw)
