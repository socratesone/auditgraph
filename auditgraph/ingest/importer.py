from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from auditgraph.errors import PathPolicyError
from auditgraph.ingest.policy import IngestionPolicy, is_allowed, matches_exclude
from auditgraph.utils.paths import contained_symlink_target, ensure_within_base


@dataclass
class ImportResult:
    """Outcome of an import collection pass.

    `allowed` and `skipped` mirror the pre-Spec-027 return shape from
    `split_imported`. `refused_symlinks` is the new Spec 027 field listing
    paths whose resolved real target escaped the workspace root.
    """

    allowed: list[Path]
    skipped: list[Path]
    refused_symlinks: list[Path]


def collect_import_paths(root: Path, targets: Iterable[str]) -> list[Path]:
    """Walk import targets and return the allowed files.

    Backwards-compatible wrapper: callers that need the refused-symlink
    list should use `collect_import_paths_with_refusals`.
    """
    return collect_import_paths_with_refusals(root, targets)[0]


def collect_import_paths_with_refusals(
    root: Path,
    targets: Iterable[str],
) -> tuple[list[Path], list[Path]]:
    """Walk import targets under root and return (files, refused_symlinks).

    Spec 027 FR-001..FR-004: every walked path's resolved target is checked
    against the workspace root. Paths whose resolved target escapes are
    collected in `refused_symlinks` rather than silently ingested.
    """
    root = root.resolve()
    files: list[Path] = []
    refused: list[Path] = []
    for target in targets:
        path = (root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
        ensure_within_base(path, root, label="import path")
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            try:
                contained_symlink_target(item, root, label="import path")
            except PathPolicyError:
                refused.append(item)
                continue
            files.append(item)
    return (
        sorted(set(files), key=lambda item: item.as_posix()),
        sorted(set(refused), key=lambda item: item.as_posix()),
    )


def split_imported(
    root: Path,
    targets: Iterable[str],
    exclude_globs: Iterable[str],
    policy: IngestionPolicy,
) -> tuple[list[Path], list[Path]]:
    """Backwards-compatible split (returns allowed, skipped only)."""
    result = split_imported_with_refusals(root, targets, exclude_globs, policy)
    return result.allowed, result.skipped


def split_imported_with_refusals(
    root: Path,
    targets: Iterable[str],
    exclude_globs: Iterable[str],
    policy: IngestionPolicy,
) -> ImportResult:
    """Spec 027 extended split: returns allowed/skipped plus refused_symlinks."""
    files, refused = collect_import_paths_with_refusals(root, targets)
    allowed: list[Path] = []
    skipped: list[Path] = []
    for path in files:
        if matches_exclude(path, root, exclude_globs):
            continue
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return ImportResult(allowed=allowed, skipped=skipped, refused_symlinks=refused)
