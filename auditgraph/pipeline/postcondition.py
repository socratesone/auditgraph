"""Spec 027 User Story 8 — pipeline redaction postcondition (FR-024..FR-028).

After `auditgraph rebuild` finishes the `index` stage, this module walks
the canonical shard directories under the active profile and re-runs the
detector set. If any match is found, the rebuild fails with a dedicated
exception that the CLI dispatch catches and translates to exit code 3,
unless `--allow-redaction-misses` was passed (then `status: "tolerated"`,
exit 0).

Shard walking and detection are delegated to the shared
`auditgraph.query._shard_scanner.scan_shards_for_misses` helper per
Constitution Principle I (DRY): the postcondition and `validate-store`
share the single source of truth for "what counts as a miss".

See `specs/027-security-hardening/contracts/postcondition-manifest.md`
for the field shape and state-machine semantics.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.query._shard_scanner import (
    CANONICAL_SHARD_DIRS,
    scan_shards_for_misses,
)
from auditgraph.utils.redaction import redaction_policy_for_config


class PostconditionFailed(RuntimeError):
    """Raised when the redaction postcondition finds matches and
    --allow-redaction-misses was NOT set. CLI dispatch translates this
    to exit code 3."""

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        miss_count = len(result.get("misses", []))
        super().__init__(
            f"redaction postcondition failed: {miss_count} miss(es) detected. "
            f"See manifest for details. Use --allow-redaction-misses to tolerate."
        )


def _count_scanned_shards(profile_root: Path) -> int:
    if not profile_root.exists():
        return 0
    total = 0
    for shard_dir_name in CANONICAL_SHARD_DIRS:
        shard_dir = profile_root / shard_dir_name
        if shard_dir.exists():
            total += sum(1 for _ in shard_dir.rglob("*.json") if _.is_file())
    return total


def skipped_result() -> dict[str, Any]:
    """Return a `redaction_postcondition` block for the `skipped` state.

    Used by `run_rebuild` when an earlier stage fails — the postcondition
    didn't actually run, but we still write an explicit entry so consumers
    can distinguish "didn't run" from "passed".
    """
    return {
        "status": "skipped",
        "misses": [],
        "allow_misses": False,
        "scanned_shards": 0,
        "wallclock_ms": 0,
    }


def run_postcondition(
    pkg_profile_root: Path,
    *,
    profile: str,
    config: Config,
    allow_misses: bool = False,
    raise_on_fail: bool = False,
) -> dict[str, Any]:
    """Walk the canonical shard dirs under ``pkg_profile_root`` and return
    the postcondition manifest block.

    Args:
        pkg_profile_root: Path like ``.pkg/profiles/default/``.
        profile: Profile name (recorded for diagnostics; same root must
            already point at this profile).
        config: Loaded config used to build the detector set via
            ``redaction_policy_for_config``.
        allow_misses: When True, misses produce ``status="tolerated"``
            instead of ``"fail"``. Operator's auditable opt-out.
        raise_on_fail: When True, raises ``PostconditionFailed`` on a
            ``"fail"`` status (used by ``run_rebuild`` to abort the
            pipeline). Default False so direct callers (tests, audit
            tooling) get the result back without an exception.

    Returns:
        A dict matching `contracts/postcondition-manifest.md` shape.
    """
    started_ns = time.monotonic_ns()
    policy = redaction_policy_for_config(config)
    detectors = list(policy.detectors)

    misses = scan_shards_for_misses(pkg_profile_root, detectors)
    scanned_shards = _count_scanned_shards(pkg_profile_root)
    elapsed_ms = int((time.monotonic_ns() - started_ns) / 1_000_000)

    if not misses:
        status = "pass"
    elif allow_misses:
        status = "tolerated"
    else:
        status = "fail"

    result: dict[str, Any] = {
        "status": status,
        "misses": misses,
        "allow_misses": bool(allow_misses),
        "scanned_shards": scanned_shards,
        "wallclock_ms": elapsed_ms,
    }

    if status == "fail" and raise_on_fail:
        raise PostconditionFailed(result)

    return result
