"""Spec-028 US6 · Wall-clock timestamps on manifests (BUG-3 fix).

Manifests gain `wall_clock_started_at` / `wall_clock_finished_at` fields
that reflect the actual invocation wall time. The existing deterministic
`started_at` / `finished_at` fields are preserved as-is to keep
`outputs_hash` stability tests passing.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import wall_clock_now


ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _scaffold(tmp_path: Path) -> Path:
    (tmp_path / "notes").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def test_wall_clock_now_returns_iso8601_within_seconds() -> None:
    before = datetime.now(timezone.utc)
    value = wall_clock_now()
    after = datetime.now(timezone.utc)
    assert ISO_PATTERN.match(value), f"wall_clock_now must return ISO-8601 UTC; got {value!r}"
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert before.timestamp() - 2 <= parsed.timestamp() <= after.timestamp() + 2


def test_wall_clock_fields_present_in_stage_manifest(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text("# Hi\n", encoding="utf-8")
    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)
    runner.run_extract(root=tmp_path, config=config)

    pkg_root = profile_pkg_root(tmp_path, config)
    for stage_manifest in (pkg_root / "runs").rglob("extract-manifest.json"):
        payload = json.loads(stage_manifest.read_text(encoding="utf-8"))
        assert "wall_clock_started_at" in payload, "stage manifests gain wall_clock_started_at"
        assert "wall_clock_finished_at" in payload
        assert ISO_PATTERN.match(payload["wall_clock_started_at"])


def test_wall_clock_fields_present_in_ingest_manifest(tmp_path: Path) -> None:
    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text("# Hi\n", encoding="utf-8")
    config = load_config(config_path)
    runner = PipelineRunner()
    result = runner.run_ingest(root=tmp_path, config=config)

    manifest = json.loads(Path(result.detail["manifest"]).read_text(encoding="utf-8"))
    assert "wall_clock_started_at" in manifest
    assert "wall_clock_finished_at" in manifest
    assert ISO_PATTERN.match(manifest["wall_clock_started_at"])


def test_deterministic_started_at_unchanged_across_runs(tmp_path: Path) -> None:
    """`started_at` must remain deterministic (hashed from run_id) — NOT
    wall-clock. Two runs against identical input produce the same
    deterministic value, while the wall-clock values differ."""
    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text("# Hi\n", encoding="utf-8")
    config = load_config(config_path)
    runner = PipelineRunner()

    # Warm cache then capture two cached-run manifests.
    runner.run_ingest(root=tmp_path, config=config)

    results = []
    for _ in range(2):
        r = runner.run_ingest(root=tmp_path, config=config)
        manifest = json.loads(Path(r.detail["manifest"]).read_text(encoding="utf-8"))
        results.append(manifest)

    # Deterministic fields identical across both runs.
    assert results[0]["started_at"] == results[1]["started_at"]
    assert results[0]["finished_at"] == results[1]["finished_at"]
    # outputs_hash also stable.
    assert results[0]["outputs_hash"] == results[1]["outputs_hash"]


def test_wall_clock_monkeypatchable_in_tests(monkeypatch, tmp_path: Path) -> None:
    """Tests can pin the wall-clock via monkeypatch to get byte-identical
    manifests for hash-stability regressions."""
    import auditgraph.storage.hashing as hashing_mod

    fixed = "2026-04-21T12:00:00Z"
    monkeypatch.setattr(hashing_mod, "wall_clock_now", lambda: fixed)

    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text("# Hi\n", encoding="utf-8")
    config = load_config(config_path)
    runner = PipelineRunner()
    result = runner.run_ingest(root=tmp_path, config=config)
    manifest = json.loads(Path(result.detail["manifest"]).read_text(encoding="utf-8"))
    assert manifest["wall_clock_started_at"] == fixed
    assert manifest["wall_clock_finished_at"] == fixed


def test_outputs_hash_stable_across_runs_with_different_wall_clocks(tmp_path: Path) -> None:
    """Invariant I7: wall-clock fields MUST NOT affect outputs_hash.

    Even though wall-clock timestamps differ between runs, outputs_hash
    stays byte-identical as long as the corpus and config are the same.
    """
    config_path = _scaffold(tmp_path)
    (tmp_path / "notes" / "intro.md").write_text("# Hi\n", encoding="utf-8")
    config = load_config(config_path)
    runner = PipelineRunner()

    # Warm cache.
    runner.run_ingest(root=tmp_path, config=config)

    # Two cached-run manifests.
    m1 = json.loads(
        Path(runner.run_ingest(root=tmp_path, config=config).detail["manifest"]).read_text(encoding="utf-8")
    )
    m2 = json.loads(
        Path(runner.run_ingest(root=tmp_path, config=config).detail["manifest"]).read_text(encoding="utf-8")
    )
    assert m1["outputs_hash"] == m2["outputs_hash"]
