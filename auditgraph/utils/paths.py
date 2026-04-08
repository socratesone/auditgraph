from __future__ import annotations

from pathlib import Path

from auditgraph.errors import PathPolicyError


def ensure_within_base(path: Path, base: Path, *, label: str = "path") -> Path:
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise PathPolicyError(f"{label} must remain within {resolved_base}") from exc
    return resolved_path


def contained_symlink_target(path: Path, base: Path, *, label: str = "ingest path") -> Path:
    """Resolve a walked path's real target and verify it stays inside ``base``.

    This is the per-path containment check used by the ingest scanner and
    importer (Spec 027 User Story 1). It follows symlink chains fully via
    ``Path.resolve(strict=False)`` and then delegates to ``ensure_within_base``
    to verify the resolved target is a descendant of the workspace root.

    Broken symlinks (whose target does not exist) still resolve to an absolute
    path textually; if that path escapes ``base`` the call raises
    ``PathPolicyError`` — which is the right outcome for FR-004 ("broken
    symlinks MUST be skipped with the same ``symlink_refused`` reason rather
    than crashing the run").
    """
    return ensure_within_base(path, base, label=label)
