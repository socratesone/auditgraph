"""Spec-028 US1 · Backward-compat reader for legacy ingest manifests.

Verifies the `_normalize_ingest_records` helper translates pre-028 cache-hit
records (parse_status="skipped" + skip_reason="unchanged_source_hash") to the
post-028 canonical shape (parse_status="ok", source_origin="cached") in memory,
without touching the on-disk manifest.

Failing state (pre-implementation): the helper does not exist; run_extract
still filters records whose parse_status != "ok" literally.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from auditgraph.ingest.policy import SKIP_REASON_UNCHANGED

LEGACY_FIXTURE = Path(__file__).parent / "fixtures" / "spec028" / "legacy_ingest_manifest.json"


def _load_legacy_fixture() -> dict:
    return json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))


def test_legacy_fixture_loads_with_expected_shape() -> None:
    """Sanity check — the fixture represents the pre-028 shape we care about."""
    data = _load_legacy_fixture()
    records = data["records"]
    assert len(records) == 4
    cached = next(r for r in records if r["path"] == "notes/cached_md.md")
    assert cached["parse_status"] == "skipped"
    assert cached["skip_reason"] == SKIP_REASON_UNCHANGED
    assert "source_origin" not in cached  # pre-028 manifests never had this


def test_legacy_cache_hit_normalizes_to_ok_cached() -> None:
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    out = _normalize_ingest_records(data["records"])
    cached = next(r for r in out if r["path"] == "notes/cached_md.md")
    assert cached["parse_status"] == "ok"
    assert cached["source_origin"] == "cached"
    # skip_reason is kept for observability even after normalization.
    assert cached["skip_reason"] == SKIP_REASON_UNCHANGED


def test_legacy_true_skip_stays_skipped() -> None:
    """Skips for reasons OTHER than cache-hit MUST stay skipped (unsupported extension, symlink refused, etc.)."""
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    out = _normalize_ingest_records(data["records"])
    unsupported = next(r for r in out if r["path"] == "notes/unsupported.exe")
    assert unsupported["parse_status"] == "skipped"
    # The helper does not invent a source_origin for genuine skips.
    assert unsupported.get("source_origin") in (None, "fresh")


def test_legacy_failed_stays_failed() -> None:
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    out = _normalize_ingest_records(data["records"])
    broken = next(r for r in out if r["path"] == "notes/broken_md.md")
    assert broken["parse_status"] == "failed"


def test_legacy_ok_records_pass_through_unchanged() -> None:
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    out = _normalize_ingest_records(data["records"])
    fresh = next(r for r in out if r["path"] == "notes/fresh_md.md")
    assert fresh["parse_status"] == "ok"
    # No source_origin was present on the legacy record; normalizer leaves it alone.
    assert "source_origin" not in fresh or fresh["source_origin"] == "fresh"


def test_normalizer_does_not_mutate_input() -> None:
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    records = data["records"]
    records_before = copy.deepcopy(records)
    _ = _normalize_ingest_records(records)
    assert records == records_before, "normalizer is pure — it does not mutate caller's list"


def test_normalizer_does_not_mutate_on_disk_manifest(tmp_path: Path) -> None:
    """FR-001/FR-002: the backward-compat reader is in-memory only; no silent migration."""
    from auditgraph.pipeline.runner import _normalize_ingest_records

    manifest_target = tmp_path / "legacy.json"
    original_bytes = LEGACY_FIXTURE.read_bytes()
    manifest_target.write_bytes(original_bytes)

    data = json.loads(manifest_target.read_text(encoding="utf-8"))
    _ = _normalize_ingest_records(data["records"])

    # On-disk file unchanged byte-for-byte.
    assert manifest_target.read_bytes() == original_bytes


def test_normalized_records_are_deterministic_list() -> None:
    """Two calls with the same input produce byte-identical output lists."""
    from auditgraph.pipeline.runner import _normalize_ingest_records

    data = _load_legacy_fixture()
    out_a = _normalize_ingest_records(data["records"])
    out_b = _normalize_ingest_records(copy.deepcopy(data["records"]))
    assert out_a == out_b
