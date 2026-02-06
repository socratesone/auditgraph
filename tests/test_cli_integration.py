from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.storage.artifacts import profile_pkg_root, read_json, write_json
from auditgraph.storage.hashing import sha256_text


def _run_cli(
    args: list[str],
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "auditgraph.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def test_cli_version_returns_value() -> None:
    result = _run_cli(["version"])
    payload = json.loads(result.stdout)

    assert payload["version"]


def test_cli_init_creates_workspace(tmp_path: Path) -> None:
    _run_cli(["init", "--root", str(tmp_path)])

    assert (tmp_path / ".pkg").exists()
    assert (tmp_path / "config" / "pkg.yaml").exists()


def test_cli_ingest_outputs_manifest(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("Hello", encoding="utf-8")

    result = _run_cli(["ingest", "--root", str(tmp_path)])
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert "ingest-manifest.json" in payload["detail"]["manifest"]


def test_cli_query_returns_results(tmp_path: Path) -> None:
    pkg_root = profile_pkg_root(tmp_path, load_config(None))
    entity_id = f"ent_{sha256_text('file:repos/app.py')}"
    index_payload = {"type": "bm25", "entries": {"app.py": [entity_id]}}
    write_json(pkg_root / "indexes" / "bm25" / "index.json", index_payload)

    result = _run_cli(["query", "--root", str(tmp_path), "--q", "app.py"])
    payload = json.loads(result.stdout)

    assert payload["results"]
    assert payload["results"][0]["id"] == entity_id


def test_cli_export_json_writes_file(tmp_path: Path) -> None:
    pkg_root = profile_pkg_root(tmp_path, load_config(None))
    entity_id = f"ent_{sha256_text('file:repos/app.py')}"
    entity = {
        "id": entity_id,
        "type": "file",
        "name": "app.py",
        "canonical_key": "file:repos/app.py",
    }
    shard = pkg_root / "entities" / entity_id[:2]
    shard.mkdir(parents=True, exist_ok=True)
    write_json(shard / f"{entity_id}.json", entity)

    result = _run_cli(["export", "--root", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)

    output_path = Path(payload["output"])
    assert output_path.exists()
    assert read_json(output_path)["entities"]


def test_cli_error_returns_status_and_message(tmp_path: Path) -> None:
    result = _run_cli(["node", "missing", "--root", str(tmp_path)], check=False)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["message"]
