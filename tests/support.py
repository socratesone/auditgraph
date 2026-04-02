from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable
import hashlib
import json

from auditgraph.config import load_config
from auditgraph.extract.entities import build_entity
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import sha256_text


DEFAULT_JOBS_YAML = """\
jobs:
  changed_since:
    action:
      type: report.changed_since
      args:
        since: 24h
    output:
      path: exports/reports/changed_since.md
"""


def run_cli(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "auditgraph.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def write_jobs_config(root: Path, content: str = DEFAULT_JOBS_YAML) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "jobs.yaml").write_text(content, encoding="utf-8")


def setup_pipeline_workspace(tmp_path: Path, title: str = "Test") -> Path:
    """Create a minimal workspace with one markdown note."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text(
        f"---\ntitle: {title}\n---\nHello world", encoding="utf-8"
    )
    return tmp_path


def read_replay_lines(pkg_root_path: Path, run_id: str) -> list[dict]:
    """Read all replay log lines for a given run."""
    replay_path = pkg_root_path / "runs" / run_id / "replay-log.jsonl"
    assert replay_path.exists(), f"replay log not found at {replay_path}"
    return [json.loads(line) for line in replay_path.read_text(encoding="utf-8").strip().splitlines()]


def pkg_root(root: Path) -> Path:
    return profile_pkg_root(root, load_config(None))


def make_entity(name: str, source_path: str) -> dict[str, object]:
    source_hash = sha256_text(f"{name}:{source_path}")
    return build_entity(
        {
            "type": "file",
            "name": name,
            "canonical_key": f"file:{source_path}",
            "source_path": source_path,
        },
        source_hash,
    )


def assert_no_secret_in_dir(base_dir: Path, secret: str, *, allowlist: Iterable[Path] | None = None) -> None:
    allowset = {path.resolve() for path in (allowlist or [])}
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() in allowset:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert secret not in content, f"Found secret in {path}"


def spec017_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "documents"


def ensure_spec017_fixtures() -> dict[str, str]:
    fixture_dir = spec017_fixture_dir()
    manifest_path = fixture_dir / "manifest.json"
    if not manifest_path.exists():
        from tests.fixtures.documents.generate_fixtures import generate

        return generate()
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def assert_spec017_fixture_checksums() -> dict[str, str]:
    expected = ensure_spec017_fixtures()
    fixture_dir = spec017_fixture_dir()
    observed: dict[str, str] = {}
    for name, checksum in expected.items():
        path = fixture_dir / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        observed[name] = digest
        assert digest == checksum
    return observed
