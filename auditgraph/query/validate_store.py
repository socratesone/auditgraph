"""Spec 027 User Story 6 — validate-store query function (FR-019..FR-022).

Audits an existing `.pkg/profiles/<profile>/` store for strings matching the
current redaction detector allowlist. Strictly read-only: never mutates any
file, never echoes matched values into the result payload.

Scope (FR-019 / Clarification Q5): only scans `entities/`, `chunks/`,
`segments/`, `documents/`, `sources/` under each selected profile. Does
NOT scan `runs/`, `indexes/`, or `secrets/`. Shard walking and detection
are delegated to `auditgraph.query._shard_scanner.scan_shards_for_misses`
per Constitution Principle I (DRY).

Output shape: see
`specs/027-security-hardening/contracts/cli-commands.md`.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.query._shard_scanner import scan_shards_for_misses
from auditgraph.utils.redaction import redaction_policy_for_config


def _list_profiles(pkg_root: Path) -> list[str]:
    """Return a sorted list of profile names under ``pkg_root/profiles/``."""
    profiles_dir = pkg_root / "profiles"
    if not profiles_dir.exists() or not profiles_dir.is_dir():
        return []
    return sorted(
        entry.name for entry in profiles_dir.iterdir() if entry.is_dir()
    )


def _scan_one_profile(
    pkg_root: Path,
    profile: str,
    detectors,
) -> dict[str, Any]:
    """Scan a single profile directory and return the per-profile result dict."""
    started_ns = time.monotonic_ns()
    profile_root = pkg_root / "profiles" / profile
    misses = scan_shards_for_misses(profile_root, detectors)
    # Count scanned shards by walking canonical dirs directly.
    from auditgraph.query._shard_scanner import CANONICAL_SHARD_DIRS

    scanned_shards = 0
    if profile_root.exists():
        for shard_dir_name in CANONICAL_SHARD_DIRS:
            shard_dir = profile_root / shard_dir_name
            if shard_dir.exists():
                scanned_shards += sum(
                    1 for _ in shard_dir.rglob("*.json") if _.is_file()
                )
    elapsed_ms = int((time.monotonic_ns() - started_ns) / 1_000_000)
    return {
        "profile": profile,
        "status": "fail" if misses else "pass",
        "misses": misses,
        "scanned_shards": scanned_shards,
        "wallclock_ms": elapsed_ms,
    }


def validate_store(
    pkg_root: Path,
    *,
    config: Config,
    profile: str | None = None,
    all_profiles: bool = False,
) -> dict[str, Any]:
    """Audit ``pkg_root`` for redaction misses.

    Args:
        pkg_root: Path to the ``.pkg`` directory (NOT ``.pkg/profiles/<name>``).
        config: Loaded config, used to resolve the active profile and to
            build the detector set via ``redaction_policy_for_config``.
        profile: Override the active profile. Mutually exclusive with
            ``all_profiles``.
        all_profiles: Scan every profile under ``pkg_root/profiles/``.
            Mutually exclusive with ``profile``.

    Returns:
        When scanning a single profile: ``{profile, status, misses,
        scanned_shards, wallclock_ms}``. When ``all_profiles=True``:
        ``{profiles: {<name>: <per_profile>}, total_misses,
        poisoned_profiles}``.

        When the store does not exist, returns ``{status: "pass",
        message: "no store to validate at <path>"}``.

    Read-only: never mutates any file. Never echoes matched secret values.
    """
    if profile and all_profiles:
        raise ValueError("profile and all_profiles are mutually exclusive")

    if not pkg_root.exists() or not (pkg_root / "profiles").exists():
        return {
            "status": "pass",
            "message": f"no store to validate at {pkg_root.as_posix()}",
            "misses": [],
        }

    policy = redaction_policy_for_config(config)
    detectors = list(policy.detectors)

    if all_profiles:
        profile_names = _list_profiles(pkg_root)
        per_profile: dict[str, dict[str, Any]] = {}
        poisoned: list[str] = []
        total_misses = 0
        for name in profile_names:
            entry = _scan_one_profile(pkg_root, name, detectors)
            per_profile[name] = entry
            total_misses += len(entry["misses"])
            if entry["status"] == "fail":
                poisoned.append(name)
        return {
            "profiles": per_profile,
            "total_misses": total_misses,
            "poisoned_profiles": poisoned,
            "status": "fail" if poisoned else "pass",
        }

    active_profile = profile or config.active_profile()
    return _scan_one_profile(pkg_root, active_profile, detectors)
