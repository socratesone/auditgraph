"""Spec-028 US4 · CLI integration tests for rule-pack validation.

`auditgraph run` must exit with code 5 and a structured JSON error when
the profile's rule_packs reference a missing or malformed file. No
silent proceed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _scaffold(tmp_path: Path, rule_pack_value: str) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n"
        "    extraction:\n"
        f"      rule_packs: [{rule_pack_value}]\n",
        encoding="utf-8",
    )
    (tmp_path / "notes" / "hi.md").write_text("# hi\n", encoding="utf-8")


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run auditgraph CLI. First arg is the subcommand. We build per-subcommand
    argument forms because subcommands don't share a unified flag scheme
    (`rebuild` uses `--root`, `run` uses positional root, etc.).
    """
    command = args[0]
    rest = list(args[1:])
    config_path = str(tmp_path / "config" / "pkg.yaml")
    if command == "run":
        # run takes positional root.
        argv = [command, str(tmp_path), "--config", config_path, *rest]
    elif command == "init":
        argv = [command, "--root", str(tmp_path), *rest]
    else:
        # rebuild / ingest / etc. use --root.
        argv = [command, "--root", str(tmp_path), "--config", config_path, *rest]
    return subprocess.run(
        [sys.executable, "-m", "auditgraph.cli", *argv],
        capture_output=True,
        text=True,
    )


def test_cli_rejects_missing_rule_pack(tmp_path: Path) -> None:
    _scaffold(tmp_path, '"config/extractors/missing.yaml"')
    result = _run_cli(tmp_path, "rebuild")
    assert result.returncode == 5, (
        f"expected exit 5 on missing rule pack; got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    # Structured JSON on stdout with code='rule_pack_missing'.
    payload = json.loads(result.stdout)
    assert payload.get("code") == "rule_pack_missing"
    assert "missing.yaml" in payload.get("path", "")


def test_cli_rejects_malformed_rule_pack(tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "bad.yaml").write_text("[unclosed\n", encoding="utf-8")
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n"
        "    extraction:\n"
        "      rule_packs: ['config/bad.yaml']\n",
        encoding="utf-8",
    )
    (tmp_path / "notes" / "hi.md").write_text("# hi\n", encoding="utf-8")

    result = _run_cli(tmp_path, "rebuild")
    assert result.returncode == 5
    payload = json.loads(result.stdout)
    assert payload.get("code") == "rule_pack_malformed"


def test_cli_default_config_succeeds(tmp_path: Path) -> None:
    """Fresh `init` produces a workspace whose config validates cleanly."""
    # Run init.
    result = _run_cli(tmp_path, "init")
    assert result.returncode == 0, f"init failed: {result.stderr}"
    # Now the workspace has config/pkg.yaml (from shipped defaults). A follow-up
    # `run` must succeed (no RulePackError).
    (tmp_path / "notes").mkdir(exist_ok=True)
    (tmp_path / "notes" / "hi.md").write_text("# hi\n", encoding="utf-8")
    result = _run_cli(tmp_path, "run")
    assert result.returncode == 0, (
        f"default config run failed: exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
