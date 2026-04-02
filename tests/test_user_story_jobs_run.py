from __future__ import annotations

import json
from pathlib import Path

from tests.support import run_cli as _run_cli, write_jobs_config as _write_jobs_config


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
