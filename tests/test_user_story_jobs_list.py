from __future__ import annotations

import json
from pathlib import Path

from tests.support import run_cli as _run_cli, write_jobs_config as _write_jobs_config


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
