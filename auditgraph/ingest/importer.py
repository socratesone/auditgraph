from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable

from auditgraph.ingest.policy import IngestionPolicy, is_allowed
from auditgraph.utils.paths import ensure_within_base


def _matches_exclude(path: Path, root: Path, exclude_globs: Iterable[str]) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_globs)


def collect_import_paths(root: Path, targets: Iterable[str]) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for target in targets:
        path = (root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
        ensure_within_base(path, root, label="import path")
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for item in path.rglob("*"):
            if item.is_file():
                files.append(item)
    return sorted(set(files), key=lambda item: item.as_posix())


def split_imported(
    root: Path,
    targets: Iterable[str],
    exclude_globs: Iterable[str],
    policy: IngestionPolicy,
) -> tuple[list[Path], list[Path]]:
    files = collect_import_paths(root, targets)
    allowed: list[Path] = []
    skipped: list[Path] = []
    for path in files:
        if _matches_exclude(path, root, exclude_globs):
            continue
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return allowed, skipped
