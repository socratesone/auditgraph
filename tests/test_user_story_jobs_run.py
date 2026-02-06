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


def _write_jobs_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "jobs.yaml").write_text(
        """jobs:
  changed_since:
    action:
      type: report.changed_since
      args:
        since: 24h
    output:
      path: exports/reports/changed_since.md
""",
        encoding="utf-8",
    )


def test_jobs_run_success(tmp_path: Path) -> None:
    _write_jobs_config(tmp_path)

    result = _run_cli(["jobs", "run", "changed_since", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["job"] == "changed_since"
    output_path = Path(payload["output"])
    assert output_path.exists()


def test_jobs_run_missing_job_returns_error(tmp_path: Path) -> None:
    _write_jobs_config(tmp_path)

    result = _run_cli(["jobs", "run", "unknown", "--root", str(tmp_path)], check=False)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["message"]
