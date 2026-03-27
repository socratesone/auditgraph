"""Schema migration support for graph artifacts.

Provides version-aware migration of graph data when the schema evolves.
Migrations are registered as functions and applied sequentially.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION

logger = logging.getLogger(__name__)

MigrationFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class MigrationStep:
    """A single schema migration step."""
    from_version: str
    to_version: str
    description: str
    fn: MigrationFn


# Registry of migration steps, ordered by version
_MIGRATIONS: list[MigrationStep] = []


def register_migration(from_version: str, to_version: str, description: str) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator to register a migration function."""
    def decorator(fn: MigrationFn) -> MigrationFn:
        _MIGRATIONS.append(MigrationStep(from_version, to_version, description, fn))
        return fn
    return decorator


def get_migration_path(from_version: str, to_version: str) -> list[MigrationStep]:
    """Find the sequence of migrations needed to go from one version to another."""
    path: list[MigrationStep] = []
    current = from_version
    seen: set[str] = set()
    while current != to_version:
        if current in seen:
            raise ValueError(f"Circular migration path detected at {current}")
        seen.add(current)
        step = next((m for m in _MIGRATIONS if m.from_version == current), None)
        if step is None:
            raise ValueError(f"No migration from {current} to {to_version}")
        path.append(step)
        current = step.to_version
    return path


def migrate(data: dict[str, Any], from_version: str, to_version: str) -> dict[str, Any]:
    """Migrate graph data from one schema version to another.

    Applies migrations sequentially. Returns the migrated data.
    Raises ValueError if no migration path exists.
    """
    if from_version == to_version:
        return data

    path = get_migration_path(from_version, to_version)
    result = data
    for step in path:
        logger.info(
            "Applying migration: %s -> %s (%s)",
            step.from_version,
            step.to_version,
            step.description,
        )
        result = step.fn(result)
        result["schema_version"] = step.to_version
    return result


def check_migration_needed(manifest_path: Path) -> bool:
    """Check if a manifest needs migration to the current schema version."""
    if not manifest_path.exists():
        return False
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = data.get("schema_version", "")
    return version != ARTIFACT_SCHEMA_VERSION
