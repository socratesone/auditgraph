from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "auditgraph.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _write_jobs_config(root: Path, content: str) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "jobs.yaml").write_text(content, encoding="utf-8")


def test_jobs_list_returns_sorted_names(tmp_path: Path) -> None:
    _write_jobs_config(
        tmp_path,
        """jobs:
  beta:
    action:
      type: report.changed_since
  alpha:
    action:
      type: report.changed_since
""",
    )

    result = _run_cli(["jobs", "list", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    assert payload["jobs"] == ["alpha", "beta"]


def test_jobs_list_invalid_config_returns_error(tmp_path: Path) -> None:
    _write_jobs_config(
        tmp_path,
        """jobs:
  broken:
    action:
      args:
        since: 24h
""",
    )

    result = _run_cli(["jobs", "list", "--root", str(tmp_path)], check=False)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["message"]
