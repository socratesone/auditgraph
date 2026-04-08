"""Spec 027 User Story 1 — hostile workspace ingest is contained.

FR-001, FR-002, FR-003, FR-004, FR-004a.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


OUTSIDE_SENTINEL = "OUTSIDE_WORKSPACE_LEAK_ZZZ"


def _build_workspace_with_escape(tmp_path: Path) -> tuple[Path, Path]:
    """Create a workspace with one regular note and one escaping symlink.

    Returns (workspace_root, target_file) where target_file is the
    escaping symlink's real target (lives OUTSIDE the workspace).
    """
    workspace = tmp_path / "workspace"
    (workspace / "notes").mkdir(parents=True)

    # Regular note to verify non-symlink files still ingest normally
    (workspace / "notes" / "ok.md").write_text(
        "# OK note\n\nThis is a regular file.\n", encoding="utf-8"
    )

    # Escaping symlink target lives outside the workspace
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    target = outside_dir / "secret.txt"
    target.write_text(
        f"secret content {OUTSIDE_SENTINEL} should never be ingested", encoding="utf-8"
    )

    link = workspace / "notes" / "leak.md"
    os.symlink(target, link)

    return workspace, target


def _run_ingest(workspace: Path):
    from auditgraph.config import load_config
    from auditgraph.pipeline.runner import PipelineRunner

    runner = PipelineRunner()
    config = load_config(None)
    return runner.run_ingest(root=workspace, config=config)


def _load_ingest_manifest(workspace: Path) -> dict:
    pkg = workspace / ".pkg" / "profiles" / "default"
    runs_dir = pkg / "runs"
    assert runs_dir.exists(), f"expected runs/ under {pkg}"
    manifests = list(runs_dir.rglob("ingest-manifest.json"))
    assert manifests, "no ingest manifest written"
    # Take the most recent one
    manifests.sort()
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _assert_sentinel_absent(workspace: Path, sentinel: str) -> None:
    pkg = workspace / ".pkg" / "profiles" / "default"
    for path in pkg.rglob("*.json"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert sentinel not in content, f"sentinel leaked into {path}"


def test_ingest_refuses_escaping_symlink(tmp_path: Path, capsys):
    workspace, _target = _build_workspace_with_escape(tmp_path)
    result = _run_ingest(workspace)
    assert result.status == "ok"

    # Manifest records show the symlink as skipped with the dedicated reason
    manifest = _load_ingest_manifest(workspace)
    records = manifest.get("records", [])
    symlink_refused_records = [
        r for r in records
        if r.get("skip_reason") == "symlink_refused"
        or r.get("status_reason") == "symlink_refused"
    ]
    assert len(symlink_refused_records) >= 1, f"expected symlink_refused in manifest records: {records}"

    # The outside-target content must NOT appear in any shard
    _assert_sentinel_absent(workspace, OUTSIDE_SENTINEL)


def test_ingest_processes_intrawork_symlink(tmp_path: Path):
    """FR-003: symlinks whose real target stays INSIDE the workspace are fine."""
    workspace = tmp_path / "workspace"
    (workspace / "notes").mkdir(parents=True)

    real = workspace / "notes" / "real.md"
    real.write_text("intra real content", encoding="utf-8")

    link = workspace / "notes" / "alias.md"
    os.symlink(real, link)

    result = _run_ingest(workspace)
    assert result.status == "ok"

    # Manifest should not contain a symlink_refused entry
    manifest = _load_ingest_manifest(workspace)
    symlink_refused = [r for r in manifest.get("records", []) if r.get("skip_reason") == "symlink_refused"]
    assert symlink_refused == []


def test_ingest_handles_broken_symlink(tmp_path: Path):
    """FR-004: broken symlinks (dangling targets) are skipped with symlink_refused, not crashes."""
    workspace = tmp_path / "workspace"
    (workspace / "notes").mkdir(parents=True)

    # Broken symlink pointing outside the workspace to a nonexistent path
    link = workspace / "notes" / "dangling.md"
    os.symlink("/tmp/definitely_does_not_exist_spec027", link)

    result = _run_ingest(workspace)
    # Must complete, not crash
    assert result.status == "ok"


def test_ingest_stderr_warning_on_refusal(tmp_path: Path, capsys):
    """FR-002: one-line WARN summary on stderr when at least one symlink was refused."""
    workspace, _ = _build_workspace_with_escape(tmp_path)
    _run_ingest(workspace)
    captured = capsys.readouterr()
    assert "WARN:" in captured.err
    assert "refused" in captured.err
    assert "symlinks pointing outside" in captured.err


def test_import_refuses_escaping_symlink(tmp_path: Path):
    """FR-001: same behavior under auditgraph import."""
    from auditgraph.config import load_config
    from auditgraph.pipeline.runner import PipelineRunner

    workspace, _ = _build_workspace_with_escape(tmp_path)
    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_import(
        root=workspace,
        config=config,
        targets=[str(workspace / "notes")],
    )
    assert result.status == "ok"
    _assert_sentinel_absent(workspace, OUTSIDE_SENTINEL)


def test_allow_symlinks_flag_raises(monkeypatch):
    """FR-004a: reserved flag must raise NotImplementedError, not silently accept."""
    from auditgraph.cli import _build_parser
    from auditgraph.cli import main as cli_main

    parser = _build_parser()
    # Test that the flag is recognized (parser accepts it)
    args = parser.parse_args(["ingest", "--allow-symlinks"])
    assert getattr(args, "allow_symlinks", False) is True

    # Invoke main via sys.argv and assert NotImplementedError surfaces
    monkeypatch.setattr("sys.argv", ["auditgraph", "ingest", "--allow-symlinks"])
    with pytest.raises(NotImplementedError, match="issue"):
        cli_main()
