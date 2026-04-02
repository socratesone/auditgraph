from __future__ import annotations

import json
from pathlib import Path

from tests.support import run_cli as _run_cli, write_jobs_config as _write_jobs_config


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


def test_job_output_traversal_rejected(tmp_path: Path) -> None:
    _write_jobs_config(
        tmp_path,
        """jobs:
  changed_since:
    action:
      type: report.changed_since
    output:
      path: ../evil.md
""",
    )

    result = _run_cli(["jobs", "run", "changed_since", "--root", str(tmp_path)], check=False)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "job output path" in payload["message"]
    assert not (tmp_path.parent / "evil.md").exists()
