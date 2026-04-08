"""Shared shard-directory scanner used by Spec 027 validate-store and pipeline postcondition.

Both `auditgraph.query.validate_store` (Phase 8 / User Story 6) and
`auditgraph.pipeline.postcondition` (Phase 10 / User Story 8) need to walk
a `.pkg/profiles/<profile>/` directory, read each sharded JSON artifact,
and report any string fields that match the current redaction detector
set. This module is their single source of truth per Constitution
Principle I (DRY).

Scope: walks only the canonical shard directories —
`entities/`, `chunks/`, `segments/`, `documents/`, `sources/`. Explicitly
does NOT scan `runs/` (pipeline manifests contain SHA-derived run IDs
that false-positive), `indexes/` (derived data; redundant), or
`secrets/` (the redactor's own HMAC key).

Miss records are `{path, category, field}` dicts. The matched value
itself is NEVER included in a miss record — this is both a privacy
requirement (don't re-persist the secret we just found) and an
attacker-log-reflection guard.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from auditgraph.utils.redaction import RedactionDetector


CANONICAL_SHARD_DIRS: tuple[str, ...] = (
    "entities",
    "chunks",
    "segments",
    "documents",
    "sources",
)


def _iter_shard_files(pkg_profile_root: Path) -> Iterable[tuple[str, Path]]:
    """Yield ``(relative_posix_path, absolute_path)`` tuples for every
    JSON file under the canonical shard directories, in sorted order."""
    if not pkg_profile_root.exists() or not pkg_profile_root.is_dir():
        return
    for shard_dir_name in CANONICAL_SHARD_DIRS:
        shard_dir = pkg_profile_root / shard_dir_name
        if not shard_dir.exists() or not shard_dir.is_dir():
            continue
        # Sort for determinism
        for path in sorted(shard_dir.rglob("*.json"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue
            rel = path.relative_to(pkg_profile_root).as_posix()
            yield rel, path


def _scan_string(text: str, detectors: Iterable[RedactionDetector]) -> list[str]:
    """Return the list of detector category names that match the given string.

    A single string can match multiple detectors; each matching category
    becomes a separate miss record in the caller's output. The matched
    substring itself is intentionally discarded — callers never see the
    secret value.
    """
    if not text:
        return []
    matched_categories: list[str] = []
    for detector in detectors:
        if detector.pattern.search(text):
            matched_categories.append(detector.category)
    return matched_categories


def _scan_document(payload: object, detectors: Iterable[RedactionDetector]) -> list[tuple[str, str]]:
    """Return a list of ``(field_name, category)`` pairs for every matching
    string field in the top-level of a shard JSON payload.

    Only top-level string fields are scanned. Deeply-nested structures
    are not recursed into because the existing shard schemas keep their
    text content at the top level (`text` for chunks, `name` for entities,
    etc.). This keeps the scan bounded and avoids false positives from
    nested metadata dicts.
    """
    if not isinstance(payload, dict):
        return []
    # Materialize detectors into a list so we can iterate multiple times
    det_list = list(detectors)
    misses: list[tuple[str, str]] = []
    for field_name, value in payload.items():
        if isinstance(value, str):
            for category in _scan_string(value, det_list):
                misses.append((field_name, category))
    return misses


def scan_shards_for_misses(
    pkg_profile_root: Path,
    detectors: Iterable[RedactionDetector],
) -> list[dict[str, str]]:
    """Scan every shard file under ``pkg_profile_root`` and return a
    sorted list of ``{path, category, field}`` miss records.

    Args:
        pkg_profile_root: A path like ``.pkg/profiles/default/``. The
            function walks only ``entities/``, ``chunks/``, ``segments/``,
            ``documents/``, ``sources/`` under this root.
        detectors: The detector set to apply (typically from
            ``_default_detectors()`` or ``Redactor.policy.detectors``).

    Returns:
        A list of dicts with keys ``path`` (POSIX relative to
        ``pkg_profile_root``), ``category`` (detector category name),
        ``field`` (top-level key of the shard JSON that held the match).
        The list is sorted by ``(path, field, category)`` for
        deterministic output.

    Never echoes the matched secret value.
    Never mutates any file.
    Never descends into ``runs/``, ``indexes/``, or ``secrets/``.
    """
    det_list = list(detectors)
    misses: list[dict[str, str]] = []

    for rel_path, abs_path in _iter_shard_files(pkg_profile_root):
        try:
            payload = json.loads(abs_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Unreadable or malformed JSON: skip silently. The scanner's
            # job is to flag credential-shaped content, not to validate
            # JSON integrity. A corrupted file is a separate concern.
            continue
        for field_name, category in _scan_document(payload, det_list):
            misses.append(
                {
                    "path": rel_path,
                    "category": category,
                    "field": field_name,
                }
            )

    # Deterministic sort: path primary, field secondary, category tertiary.
    misses.sort(key=lambda m: (m["path"], m["field"], m["category"]))
    return misses
