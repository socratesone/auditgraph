from __future__ import annotations

from pathlib import Path

from auditgraph.errors import PathPolicyError


def resolve_within_base(path: Path, base: Path, *, label: str = "path") -> Path:
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise PathPolicyError(f"{label} must remain within {resolved_base}") from exc
    return resolved_path


def ensure_within_base(path: Path, base: Path, *, label: str = "path") -> Path:
    return resolve_within_base(path, base, label=label)
