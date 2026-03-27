from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.ingest.policy import IngestionPolicy, is_allowed, matches_exclude
from auditgraph.utils.paths import ensure_within_base


def discover_files(root: Path, include_paths: Iterable[str], exclude_globs: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    root = root.resolve()
    for include in include_paths:
        base = (root / include).resolve()
        ensure_within_base(base, root, label="include path")
        if not base.exists():
            continue
        if base.is_file():
            files.append(base)
            continue
        for path in base.rglob("*"):
            if path.is_file():
                files.append(path)

    filtered = [path for path in files if not matches_exclude(path, root, exclude_globs)]
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
