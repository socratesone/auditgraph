from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable

from auditgraph.ingest.policy import IngestionPolicy, is_allowed


def _matches_exclude(path: Path, root: Path, exclude_globs: Iterable[str]) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_globs)


def discover_files(root: Path, include_paths: Iterable[str], exclude_globs: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    root = root.resolve()
    for include in include_paths:
        base = (root / include).resolve()
        if not base.exists():
            continue
        if base.is_file():
            files.append(base)
            continue
        for path in base.rglob("*"):
            if path.is_file():
                files.append(path)

    filtered = [path for path in files if not _matches_exclude(path, root, exclude_globs)]
    return sorted(filtered, key=lambda item: item.as_posix())


def split_allowed(paths: Iterable[Path], policy: IngestionPolicy) -> tuple[list[Path], list[Path]]:
    allowed: list[Path] = []
    skipped: list[Path] = []
    for path in paths:
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return allowed, skipped
