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


def test_job_output_default_path(tmp_path: Path) -> None:
    _write_jobs_config(
        tmp_path,
        """jobs:
  changed_since:
    action:
      type: report.changed_since
      args:
        since: 24h
""",
    )

    result = _run_cli(["jobs", "run", "changed_since", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    output_path = Path(payload["output"])
    assert output_path == (tmp_path / "exports" / "reports" / "changed_since.md")


def test_job_output_override_path(tmp_path: Path) -> None:
    _write_jobs_config(
        tmp_path,
        """jobs:
  changed_since:
    action:
      type: report.changed_since
    output:
      path: exports/reports/custom.md
""",
    )

    result = _run_cli(["jobs", "run", "changed_since", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    output_path = Path(payload["output"])
    assert output_path == (tmp_path / "exports" / "reports" / "custom.md")
