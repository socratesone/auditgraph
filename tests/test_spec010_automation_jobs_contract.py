from __future__ import annotations

import json
from pathlib import Path

from tests.support import run_cli as _run_cli, write_jobs_config as _write_jobs_config


def test_jobs_run_response_contract(tmp_path: Path) -> None:
    _write_jobs_config(tmp_path)

    result = _run_cli(["jobs", "run", "changed_since", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["job"]
    assert payload["output"]


def test_jobs_error_response_contract(tmp_path: Path) -> None:
    _write_jobs_config(tmp_path)

    result = _run_cli(["jobs", "run", "missing", "--root", str(tmp_path)], check=False)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["message"]


def test_jobs_list_response_contract(tmp_path: Path) -> None:
    _write_jobs_config(tmp_path)

    result = _run_cli(["jobs", "list", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    assert isinstance(payload["jobs"], list)
