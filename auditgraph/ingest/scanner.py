from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from auditgraph.errors import PathPolicyError
from auditgraph.ingest.policy import IngestionPolicy, is_allowed, matches_exclude
from auditgraph.utils.paths import contained_symlink_target, ensure_within_base


@dataclass
class DiscoverResult:
    """Outcome of a discovery walk.

    `files` is the list of walked files whose real target stays inside the
    workspace root (same as the pre-Spec-027 return value). `refused_symlinks`
    is the new Spec 027 field listing paths that were skipped because their
    resolved symlink target escaped the workspace root (or the target was
    missing entirely — both cases map to `skip_reason: symlink_refused`).
    """

    files: list[Path]
    refused_symlinks: list[Path]


def discover_files(
    root: Path,
    include_paths: Iterable[str],
    exclude_globs: Iterable[str],
) -> list[Path]:
    """Walk include_paths under root and return the allowed files list.

    Backwards-compatible thin wrapper around `discover_files_with_refusals`.
    Callers that need the list of refused escaping symlinks should call
    the explicit function instead.
    """
    return discover_files_with_refusals(root, include_paths, exclude_globs).files


def discover_files_with_refusals(
    root: Path,
    include_paths: Iterable[str],
    exclude_globs: Iterable[str],
) -> DiscoverResult:
    """Walk include_paths under root and return allowed files + refused symlinks.

    Spec 027 FR-001..FR-004: every walked path is checked against the workspace
    root via `contained_symlink_target`. Paths whose resolved real target
    escapes the root are collected in `refused_symlinks` rather than added to
    the file list, so the caller can emit a `symlink_refused` skip-reason and
    the one-line stderr summary.
    """
    files: list[Path] = []
    refused: list[Path] = []
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
            if not path.is_file():
                continue
            try:
                contained_symlink_target(path, root, label="ingest path")
            except PathPolicyError:
                refused.append(path)
                continue
            files.append(path)

    filtered = [path for path in files if not matches_exclude(path, root, exclude_globs)]
    return DiscoverResult(
        files=sorted(filtered, key=lambda item: item.as_posix()),
        refused_symlinks=sorted(refused, key=lambda item: item.as_posix()),
    )


def split_allowed(paths: Iterable[Path], policy: IngestionPolicy) -> tuple[list[Path], list[Path]]:
    allowed: list[Path] = []
    skipped: list[Path] = []
    for path in paths:
        if is_allowed(path, policy):
            allowed.append(path)
        else:
            skipped.append(path)
    return allowed, skipped
