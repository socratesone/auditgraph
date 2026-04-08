"""Spec 027 FR-029 / FR-030 — pyproject.toml dependency baseline.

Asserts the pinned parser dependencies and the new jsonschema runtime
dependency are present in pyproject.toml at the required lower bounds.

On Python 3.10, stdlib `tomllib` is unavailable and the test is skipped
cleanly via `pytest.importorskip`. The spec rejected adding `tomli` as
a new dev dependency for a test that becomes trivial on 3.11+.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _load_pyproject() -> dict:
    tomllib = pytest.importorskip(
        "tomllib",
        reason="tomllib is stdlib on Python 3.11+; skipped on earlier versions",
    )
    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _deps(pyproject: dict) -> list[str]:
    return list(pyproject.get("project", {}).get("dependencies", []))


def _find_dep(deps: list[str], name: str) -> str | None:
    prefix_lower = name.lower()
    for entry in deps:
        # Split on any specifier character to isolate the package name
        head = entry.split(";")[0].strip()
        token = head.split(">")[0].split("<")[0].split("=")[0].split("!")[0].split("~")[0].strip()
        if token.lower() == prefix_lower:
            return head
    return None


def test_jsonschema_dependency_pinned():
    """FR-030: jsonschema>=4,<5 MUST be declared as a runtime dependency."""
    deps = _deps(_load_pyproject())
    entry = _find_dep(deps, "jsonschema")
    assert entry is not None, f"jsonschema not found in pyproject.toml dependencies: {deps}"
    assert ">=4" in entry, f"jsonschema entry missing >=4 lower bound: {entry}"
    assert "<5" in entry, f"jsonschema entry missing <5 upper bound: {entry}"


def test_pyyaml_lower_bound():
    """FR-029: pyyaml must be pinned at >=6.0.3 (post-Spec-025 audit baseline)."""
    deps = _deps(_load_pyproject())
    entry = _find_dep(deps, "pyyaml")
    assert entry is not None, f"pyyaml not found in pyproject.toml dependencies: {deps}"
    assert ">=6.0.3" in entry, f"pyyaml entry missing >=6.0.3 lower bound: {entry}"


def test_pypdf_lower_bound():
    """FR-029: pypdf must be pinned at >=6.9.1 (post-Spec-025 audit baseline)."""
    deps = _deps(_load_pyproject())
    entry = _find_dep(deps, "pypdf")
    assert entry is not None, f"pypdf not found in pyproject.toml dependencies: {deps}"
    assert ">=6.9.1" in entry, f"pypdf entry missing >=6.9.1 lower bound: {entry}"


def test_python_docx_lower_bound():
    """FR-029: python-docx must be pinned at >=1.2.0 (post-Spec-025 audit baseline)."""
    deps = _deps(_load_pyproject())
    entry = _find_dep(deps, "python-docx")
    assert entry is not None, f"python-docx not found in pyproject.toml dependencies: {deps}"
    assert ">=1.2.0" in entry, f"python-docx entry missing >=1.2.0 lower bound: {entry}"
