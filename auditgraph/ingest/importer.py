from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.ingest.policy import IngestionPolicy, is_allowed, matches_exclude
from auditgraph.utils.paths import ensure_within_base


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
        if matches_exclude(path, root, exclude_globs):
            continue
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return allowed, skipped
