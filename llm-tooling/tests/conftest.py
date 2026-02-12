"""Shared fixtures for MCP tooling contract tests."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


@pytest.fixture()
def manifest_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tool.manifest.json"


repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
