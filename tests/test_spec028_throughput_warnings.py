"""Spec-028 US3 · Throughput warning tests (FR-017 through FR-020).

Binary threshold: a stage emits a structured warning iff it received
≥1 input from the prior stage AND produced exactly 0 output. The
warnings are surfaced in TWO places per contracts/stage-manifest-warnings.md:

- live StageResult.detail["warnings"] — MAY be omitted when empty
- persisted <stage>-manifest.json top-level `warnings` key — ALWAYS
  serialized as a list (even `[]`).

Neither location participates in outputs_hash (Invariant I7).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.pipeline.warnings import (
    THROUGHPUT_WARNING_EMPTY_INDEX,
    THROUGHPUT_WARNING_NO_ENTITIES,
    warning_empty_index,
    warning_no_entities,
)
from auditgraph.storage.artifacts import profile_pkg_root


def _scaffold(tmp_path: Path, allowed_extensions: list[str], markdown_enabled: bool) -> Path:
    (tmp_path / "content").mkdir(exist_ok=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    ext_list = "[" + ", ".join(f'"{e}"' for e in allowed_extensions) + "]"
    md_flag = "true" if markdown_enabled else "false"
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [content]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        f"      allowed_extensions: {ext_list}\n"
        "    extraction:\n"
        "      ner:\n        enabled: false\n"
        f"      markdown:\n        enabled: {md_flag}\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def test_warning_helpers_produce_expected_codes() -> None:
    w = warning_no_entities(17)
    assert w.code == THROUGHPUT_WARNING_NO_ENTITIES
    assert "17" in w.message
    assert w.hint

    w2 = warning_empty_index(5)
    assert w2.code == THROUGHPUT_WARNING_EMPTY_INDEX
    assert "5" in w2.message
    assert w2.hint


def test_zero_entities_from_nonzero_input_emits_warning(tmp_path: Path) -> None:
    """.txt input with markdown disabled and no other producers → 0 entities.

    The corpus must pass ingest (≥1 ok record) but produce zero entities
    in extract to trigger FR-017's binary threshold.
    """
    config_path = _scaffold(tmp_path, allowed_extensions=[".txt"], markdown_enabled=False)
    (tmp_path / "content" / "hello.txt").write_text("hello world\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    result = runner.run_extract(root=tmp_path, config=config, run_id=run_id)

    warnings = result.detail.get("warnings") or []
    codes = [w["code"] for w in warnings]
    assert THROUGHPUT_WARNING_NO_ENTITIES in codes, (
        f"expected no_entities_produced warning, got: {codes}"
    )


def test_one_entity_from_nonzero_input_emits_no_warning(tmp_path: Path) -> None:
    """A markdown file produces at least a note entity → no warning."""
    config_path = _scaffold(tmp_path, allowed_extensions=[".md"], markdown_enabled=True)
    (tmp_path / "content" / "note.md").write_text("# Hello\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    result = runner.run_extract(root=tmp_path, config=config, run_id=run_id)

    warnings = result.detail.get("warnings") or []
    codes = [w["code"] for w in warnings]
    assert THROUGHPUT_WARNING_NO_ENTITIES not in codes


def test_warning_persists_to_manifest(tmp_path: Path) -> None:
    """Warnings appear under the top-level `warnings` key in the persisted
    stage manifest — always as a list (even when empty)."""
    config_path = _scaffold(tmp_path, allowed_extensions=[".txt"], markdown_enabled=False)
    (tmp_path / "content" / "hello.txt").write_text("hello\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    result = runner.run_extract(root=tmp_path, config=config, run_id=run_id)

    pkg_root = profile_pkg_root(tmp_path, config)
    manifest_path = pkg_root / "runs" / run_id / "extract-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "warnings" in manifest, "top-level `warnings` key MUST always be present"
    assert isinstance(manifest["warnings"], list)
    codes = [w["code"] for w in manifest["warnings"]]
    assert THROUGHPUT_WARNING_NO_ENTITIES in codes


def test_empty_warnings_serialized_as_empty_list(tmp_path: Path) -> None:
    """Happy-path run: `warnings` key present as [] (always-serialized)."""
    config_path = _scaffold(tmp_path, allowed_extensions=[".md"], markdown_enabled=True)
    (tmp_path / "content" / "note.md").write_text("# Hello\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    runner.run_extract(root=tmp_path, config=config, run_id=run_id)

    pkg_root = profile_pkg_root(tmp_path, config)
    manifest_path = pkg_root / "runs" / run_id / "extract-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "warnings" in manifest
    assert manifest["warnings"] == []


def test_warning_does_not_change_exit_code(tmp_path: Path) -> None:
    """FR-019: warnings MUST NOT change stage status — it stays 'ok'."""
    config_path = _scaffold(tmp_path, allowed_extensions=[".txt"], markdown_enabled=False)
    (tmp_path / "content" / "hello.txt").write_text("hello\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
    result = runner.run_extract(root=tmp_path, config=config, run_id=run_id)
    assert result.status == "ok"


def test_warning_does_not_affect_outputs_hash(tmp_path: Path) -> None:
    """Invariant I7: warnings are not in outputs_hash."""
    config_path = _scaffold(tmp_path, allowed_extensions=[".txt"], markdown_enabled=False)
    (tmp_path / "content" / "hello.txt").write_text("hello\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    # Run twice; outputs_hash for extract manifests must match.
    hashes = []
    for _ in range(2):
        ingest = runner.run_ingest(root=tmp_path, config=config)
        run_id = json.loads(Path(ingest.detail["manifest"]).read_text(encoding="utf-8"))["run_id"]
        runner.run_extract(root=tmp_path, config=config, run_id=run_id)
        pkg_root = profile_pkg_root(tmp_path, config)
        manifest = json.loads(
            (pkg_root / "runs" / run_id / "extract-manifest.json").read_text(encoding="utf-8")
        )
        hashes.append(manifest["outputs_hash"])
    assert hashes[0] == hashes[1], "outputs_hash drifted despite identical inputs"
