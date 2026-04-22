"""Spec-028 US4 · `auditgraph init` copies rule-pack stubs.

Per contracts/rule-pack-validator.md, `initialize_workspace` must copy
BOTH the pkg.yaml AND the two rule-pack stubs into a new workspace.
Stubs are sourced from the `auditgraph/_package_data/` package tree via
`importlib.resources`.
"""
from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest

from auditgraph.scaffold import initialize_workspace


@pytest.fixture()
def config_source(tmp_path_factory) -> Path:
    """A fake config_source pointing to a minimal pkg.yaml."""
    src = tmp_path_factory.mktemp("config_src") / "pkg.yaml"
    src.write_text("pkg_root: .\n", encoding="utf-8")
    return src


def test_init_creates_pkg_yaml(tmp_path: Path, config_source: Path) -> None:
    created = initialize_workspace(tmp_path, config_source)
    assert (tmp_path / "config" / "pkg.yaml").exists()
    assert str(tmp_path / "config" / "pkg.yaml") in created


def test_init_creates_extractors_stub(tmp_path: Path, config_source: Path) -> None:
    initialize_workspace(tmp_path, config_source)
    stub = tmp_path / "config" / "extractors" / "core.yaml"
    assert stub.exists(), "init must copy the shipped extractors/core.yaml stub"
    text = stub.read_text(encoding="utf-8")
    assert "version" in text


def test_init_creates_link_rules_stub(tmp_path: Path, config_source: Path) -> None:
    initialize_workspace(tmp_path, config_source)
    stub = tmp_path / "config" / "link_rules" / "core.yaml"
    assert stub.exists(), "init must copy the shipped link_rules/core.yaml stub"
    text = stub.read_text(encoding="utf-8")
    assert "version" in text


def test_init_is_idempotent_on_existing_stub(tmp_path: Path, config_source: Path) -> None:
    """Pre-existing stubs are NOT overwritten (scaffold is idempotent)."""
    stub = tmp_path / "config" / "extractors" / "core.yaml"
    stub.parent.mkdir(parents=True)
    stub.write_text("# custom user content\nversion: v1\n", encoding="utf-8")

    initialize_workspace(tmp_path, config_source)
    assert stub.read_text(encoding="utf-8") == "# custom user content\nversion: v1\n"


def test_init_stub_content_matches_package_resource_byte_identically(
    tmp_path: Path, config_source: Path
) -> None:
    initialize_workspace(tmp_path, config_source)
    local_stub = (tmp_path / "config" / "extractors" / "core.yaml").read_text(encoding="utf-8")
    # Compare against the package resource.
    resource = importlib.resources.files("auditgraph") / "_package_data" / "config" / "extractors" / "core.yaml"
    shipped = resource.read_text(encoding="utf-8")
    assert local_stub == shipped
