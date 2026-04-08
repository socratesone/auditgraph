"""Spec 027 User Story 3 — export-neo4j output path containment (FR-010).

`auditgraph export-neo4j --output <path>` MUST refuse any `--output` target
whose resolved path escapes `<root>/exports/neo4j/`. This mirrors the
`auditgraph export` handler.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from auditgraph.cli import main as cli_main
from auditgraph.config import load_config
from auditgraph.storage.artifacts import profile_pkg_root
from tests.fixtures.neo4j_fixtures import write_test_graph


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Build a minimal workspace containing a tiny graph ready for export."""
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)
    return tmp_path


def _run_cli(workspace: Path, monkeypatch, *extra_args: str) -> int:
    """Invoke `cli_main` inside `workspace` with the given extra argv."""
    monkeypatch.chdir(workspace)
    argv = ["auditgraph", "export-neo4j", "--root", str(workspace), *extra_args]
    monkeypatch.setattr("sys.argv", argv)
    try:
        cli_main()
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    return 0


def test_external_absolute_output_refused(workspace, monkeypatch, capsys):
    escape = "/tmp/auditgraph_spec027_escape.cypher"
    # Ensure it doesn't exist from a prior test
    if os.path.exists(escape):
        os.remove(escape)

    rc = _run_cli(workspace, monkeypatch, "--output", escape)
    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()
    assert rc != 0, f"expected non-zero exit, got rc={rc}. out={captured.out} err={captured.err}"
    assert "must remain within" in combined, f"missing containment error. output={combined}"
    assert not os.path.exists(escape), "escape file was created despite containment check"


def test_workspace_relative_output_accepted(workspace, monkeypatch):
    rc = _run_cli(workspace, monkeypatch, "--output", "exports/neo4j/out.cypher")
    assert rc == 0, f"expected success, got rc={rc}"
    assert (workspace / "exports" / "neo4j" / "out.cypher").exists()


def test_default_output_path(workspace, monkeypatch):
    rc = _run_cli(workspace, monkeypatch)
    assert rc == 0, f"expected success, got rc={rc}"
    assert (workspace / "exports" / "neo4j" / "export.cypher").exists()
