"""Spec 027 FR-001 / FR-004 — contained_symlink_target helper."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from auditgraph.errors import PathPolicyError


def test_file_inside_base_returns_resolved(tmp_path: Path):
    from auditgraph.utils.paths import contained_symlink_target

    (tmp_path / "notes").mkdir()
    real_file = tmp_path / "notes" / "ok.md"
    real_file.write_text("hello", encoding="utf-8")

    resolved = contained_symlink_target(real_file, tmp_path)
    assert resolved == real_file.resolve()


def test_symlink_to_file_outside_raises(tmp_path: Path):
    from auditgraph.utils.paths import contained_symlink_target

    outside_dir = tmp_path.parent / f"{tmp_path.name}_outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    (tmp_path / "notes").mkdir()
    link = tmp_path / "notes" / "leak.md"
    os.symlink(outside_file, link)

    with pytest.raises(PathPolicyError):
        contained_symlink_target(link, tmp_path)

    # Cleanup since we stepped outside tmp_path's lifecycle
    outside_file.unlink()
    outside_dir.rmdir()


def test_broken_symlink_raises(tmp_path: Path):
    from auditgraph.utils.paths import contained_symlink_target

    (tmp_path / "notes").mkdir()
    link = tmp_path / "notes" / "dangling.md"
    # Target deliberately does not exist AND is outside the workspace
    os.symlink("/tmp/does_not_exist_spec027_test", link)

    with pytest.raises(PathPolicyError):
        contained_symlink_target(link, tmp_path)


def test_symlink_chain_escaping_raises(tmp_path: Path):
    from auditgraph.utils.paths import contained_symlink_target

    outside_dir = tmp_path.parent / f"{tmp_path.name}_outside2"
    outside_dir.mkdir()
    target = outside_dir / "final.txt"
    target.write_text("final", encoding="utf-8")

    (tmp_path / "notes").mkdir()
    first = tmp_path / "notes" / "first.md"
    os.symlink(target, first)

    second = tmp_path / "notes" / "second.md"
    os.symlink(first, second)

    with pytest.raises(PathPolicyError):
        contained_symlink_target(second, tmp_path)

    target.unlink()
    outside_dir.rmdir()


def test_intrawork_symlink_returns_resolved(tmp_path: Path):
    """Intra-workspace symlinks should resolve successfully (FR-003 guard)."""
    from auditgraph.utils.paths import contained_symlink_target

    (tmp_path / "notes").mkdir()
    real = tmp_path / "notes" / "real.md"
    real.write_text("real", encoding="utf-8")

    link = tmp_path / "notes" / "alias.md"
    os.symlink(real, link)

    resolved = contained_symlink_target(link, tmp_path)
    assert resolved == real.resolve()
