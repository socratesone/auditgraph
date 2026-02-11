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


def test_export_output_path_traversal_rejected(tmp_path: Path) -> None:
    result = _run_cli(
        ["export", "--root", str(tmp_path), "--format", "json", "--output", "../evil.json"],
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "export output path" in payload["message"]
    assert not (tmp_path.parent / "evil.json").exists()
