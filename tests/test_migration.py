"""Tests for schema migration support."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.storage.migration import (
    check_migration_needed,
    get_migration_path,
    migrate,
    register_migration,
    _MIGRATIONS,
)
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION


@pytest.fixture(autouse=True)
def _clear_migrations():
    """Clear migration registry between tests."""
    original = _MIGRATIONS.copy()
    _MIGRATIONS.clear()
    yield
    _MIGRATIONS.clear()
    _MIGRATIONS.extend(original)


def test_migrate_noop_when_same_version() -> None:
    """No migration needed when versions match."""
    data = {"schema_version": "v1", "entities": []}
    result = migrate(data, "v1", "v1")
    assert result is data


def test_migrate_applies_registered_step() -> None:
    """Migration function is applied and version is stamped."""
    @register_migration("v1", "v2", "add default_field")
    def _add_field(data):
        data["default_field"] = True
        return data

    data = {"schema_version": "v1", "entities": []}
    result = migrate(data, "v1", "v2")
    assert result["schema_version"] == "v2"
    assert result["default_field"] is True


def test_migrate_chains_multiple_steps() -> None:
    """Multiple migration steps are applied in order."""
    @register_migration("v1", "v2", "step 1")
    def _step1(data):
        data["step1"] = True
        return data

    @register_migration("v2", "v3", "step 2")
    def _step2(data):
        data["step2"] = True
        return data

    data = {"schema_version": "v1"}
    result = migrate(data, "v1", "v3")
    assert result["schema_version"] == "v3"
    assert result["step1"] is True
    assert result["step2"] is True


def test_migrate_raises_on_missing_path() -> None:
    """ValueError when no migration path exists."""
    with pytest.raises(ValueError, match="No migration from"):
        migrate({}, "v1", "v99")


def test_get_migration_path_detects_cycle() -> None:
    """Circular migration paths are detected."""
    @register_migration("v1", "v2", "forward")
    def _fwd(data):
        return data

    @register_migration("v2", "v1", "backward")
    def _bwd(data):
        return data

    with pytest.raises(ValueError, match="Circular migration path"):
        get_migration_path("v1", "v3")  # v1→v2→v1 cycle, never reaches v3


def test_check_migration_needed_false_for_current(tmp_path: Path) -> None:
    """No migration needed when manifest has current schema version."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": ARTIFACT_SCHEMA_VERSION}))
    assert check_migration_needed(manifest) is False


def test_check_migration_needed_true_for_old(tmp_path: Path) -> None:
    """Migration needed when manifest has old schema version."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": "v0"}))
    assert check_migration_needed(manifest) is True


def test_check_migration_needed_false_for_missing(tmp_path: Path) -> None:
    """No migration needed when manifest doesn't exist."""
    assert check_migration_needed(tmp_path / "nonexistent.json") is False
