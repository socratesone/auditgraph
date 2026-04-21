"""Spec-028 US1 · BUG-1 cache-skip regression tests.

Exercises FR-001 through FR-005 via the `IngestRecord` dataclass and the
`build_source_record` producer. Verifies that the new `source_origin` field
separates cache-hit vs fresh-parse execution origin from the `parse_status`
correctness signal.

Failing state (pre-implementation): IngestRecord has no `source_origin` field;
`build_source_record` has no `source_origin` keyword; the cache-hit branch in
`run_ingest` still writes `parse_status="skipped"` for cached records.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.ingest.policy import SKIP_REASON_UNCHANGED
from auditgraph.ingest.sources import build_source_record
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.manifests import IngestRecord

from tests.support import null_parse_options  # noqa: F401 (available for downstream tests)


def _make_config(tmp_path: Path) -> tuple[Path, Path]:
    """Scaffold a tiny workspace rooted at tmp_path. Returns (root, config_path)."""
    root = tmp_path
    (root / "notes").mkdir()
    config_path = root / "config" / "pkg.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
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
    return root, config_path


def _only_record_for(manifest_path: Path, relative_path: str) -> dict:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = [r for r in payload["records"] if r["path"] == relative_path]
    assert len(records) == 1, f"expected exactly one record for {relative_path}, got {len(records)}"
    return records[0]


def test_cache_hit_sets_parse_status_ok_and_source_origin_cached(tmp_path: Path) -> None:
    root, config_path = _make_config(tmp_path)
    (root / "notes" / "intro.md").write_text("# Intro\n\nhello world\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(config_path)

    # First run — fresh parse.
    result_1 = runner.run_ingest(root=root, config=config)
    assert result_1.status == "ok"
    manifest_path_1 = Path(result_1.detail["manifest"])
    rec_1 = _only_record_for(manifest_path_1, "notes/intro.md")
    assert rec_1["parse_status"] == "ok"
    assert rec_1.get("source_origin") == "fresh"

    # Second run — cache hit on the same file. This is the regression path:
    # pre-028 it produced parse_status="skipped" (BUG-1), extract dropped it.
    result_2 = runner.run_ingest(root=root, config=config)
    assert result_2.status == "ok"
    manifest_path_2 = Path(result_2.detail["manifest"])
    rec_2 = _only_record_for(manifest_path_2, "notes/intro.md")
    assert rec_2["parse_status"] == "ok", (
        "cache hit MUST keep parse_status='ok' — cached is not the same as skipped (FR-001)"
    )
    assert rec_2.get("source_origin") == "cached"
    assert rec_2.get("skip_reason") == SKIP_REASON_UNCHANGED, (
        "observability field stays put (FR-002); downstream stages use parse_status not skip_reason"
    )


def test_cache_hit_is_consumed_by_extract(tmp_path: Path) -> None:
    """Extract MUST produce entities from cached-but-ok markdown sources (FR-003)."""
    root, config_path = _make_config(tmp_path)
    (root / "notes" / "intro.md").write_text("# Intro\n\nhello\n", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(config_path)

    # Run the full pipeline once.
    runner.run_ingest(root=root, config=config)
    result_extract_1 = runner.run_extract(root=root, config=config)
    assert result_extract_1.status == "ok"

    # Count entities written.
    entities_dir = root / ".pkg" / "profiles" / "default" / "entities"
    n_1 = len(list(entities_dir.rglob("ent_*.json"))) if entities_dir.exists() else 0
    assert n_1 > 0, "first run should produce at least one entity from markdown"

    # Second pipeline run — cache kicks in for ingest; extract must still process.
    runner.run_ingest(root=root, config=config)
    runner.run_extract(root=root, config=config)
    n_2 = len(list(entities_dir.rglob("ent_*.json")))
    assert n_2 == n_1, (
        f"entity count must stay constant across reruns (got {n_1} then {n_2}); "
        "BUG-1 caused the second count to drop to 0"
    )


def test_fresh_failed_parse_stays_failed_and_fresh(tmp_path: Path) -> None:
    """Parse failures MUST record parse_status='failed' + source_origin='fresh'.

    Uses build_source_record directly as a unit-level assertion — failures come
    from many sites (docx/pdf backends, unsupported docs, etc.), but all flow
    through this producer.
    """
    path = tmp_path / "notes" / "stub.md"
    path.parent.mkdir(parents=True)
    path.write_text("stub\n", encoding="utf-8")

    record, metadata = build_source_record(
        path,
        root=tmp_path,
        parser_id="text/markdown",
        parse_status="failed",
        status_reason="simulated_failure",
        skip_reason=None,
    )
    assert isinstance(record, IngestRecord)
    assert record.parse_status == "failed"
    assert record.source_origin == "fresh", (
        "parse failures are always fresh (a parse must be attempted to fail). "
        "Invariant I6: parse_status='failed' ⇒ source_origin='fresh'."
    )
    assert metadata["parse_status"] == "failed"
    assert metadata["source_origin"] == "fresh"


def test_unsupported_extension_stays_skipped_and_fresh(tmp_path: Path) -> None:
    path = tmp_path / "notes" / "thing.exe"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x00\x00")

    record, _ = build_source_record(
        path,
        root=tmp_path,
        parser_id="text/unknown",
        parse_status="skipped",
        status_reason="unsupported_extension",
        skip_reason="unsupported_extension",
    )
    assert record.parse_status == "skipped"
    # Unsupported-extension skips are genuine skips — the file was seen but
    # not parsed. Default origin is "fresh" (no cache hit happened).
    assert record.source_origin == "fresh"


def test_source_origin_default_is_fresh(tmp_path: Path) -> None:
    """Callers that don't pass source_origin get the fresh default (backward-compat)."""
    path = tmp_path / "notes" / "a.md"
    path.parent.mkdir(parents=True)
    path.write_text("a\n", encoding="utf-8")

    record, _ = build_source_record(
        path,
        root=tmp_path,
        parser_id="text/markdown",
        parse_status="ok",
    )
    assert record.source_origin == "fresh"


def test_source_origin_is_keyword_only(tmp_path: Path) -> None:
    """Guard against accidental positional use that would collide with skip_reason.

    `source_origin` MUST be passed as a kwarg. Attempting to pass it positionally
    after `parse_status` raises TypeError.
    """
    path = tmp_path / "notes" / "a.md"
    path.parent.mkdir(parents=True)
    path.write_text("a\n", encoding="utf-8")

    with pytest.raises(TypeError):
        # 8 positional args would include source_origin in an unintended slot.
        build_source_record(path, tmp_path, "text/markdown", "ok", None, None, None, "cached")  # noqa
