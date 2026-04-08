"""Spec 027 T010a — shared shard scanner helper.

Tests for `auditgraph.query._shard_scanner.scan_shards_for_misses`.
This helper is shared by `validate_store.py` (Phase 8) and
`pipeline/postcondition.py` (Phase 10) to avoid duplicating the
walk+detect logic (Constitution Principle I — DRY).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_shard(
    pkg_profile_root: Path,
    shard_dir_name: str,
    entity_id: str,
    payload: dict,
) -> Path:
    shard = pkg_profile_root / shard_dir_name / entity_id[:2]
    shard.mkdir(parents=True, exist_ok=True)
    path = shard / f"{entity_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _clean_chunk(cid: str, text: str = "a regular note with nothing sensitive") -> dict:
    return {
        "chunk_id": cid,
        "document_id": "doc_a",
        "text": text,
        "order": 0,
        "source_path": "notes/a.md",
        "source_hash": "abcd",
    }


def test_clean_profile_returns_empty(tmp_path: Path):
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    pkg_profile = tmp_path / ".pkg" / "profiles" / "default"
    _write_shard(pkg_profile, "chunks", "chk_aa1234", _clean_chunk("chk_aa1234"))

    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(pkg_profile, detectors)
    assert misses == []


def test_poisoned_chunk_returns_one_miss(tmp_path: Path):
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    pkg_profile = tmp_path / ".pkg" / "profiles" / "default"
    poisoned = _clean_chunk("chk_bb5678", text="incident notes password=LEAKED_VALUE_XYZ end")
    _write_shard(pkg_profile, "chunks", "chk_bb5678", poisoned)

    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(pkg_profile, detectors)

    assert len(misses) == 1
    m = misses[0]
    assert set(m.keys()) == {"path", "category", "field"}
    assert m["path"].startswith("chunks/")
    assert m["path"].endswith("chk_bb5678.json")
    assert m["category"] == "credential"
    assert m["field"] == "text"


def test_scope_excludes_runs_indexes_secrets(tmp_path: Path):
    """Files under runs/, indexes/, secrets/ must NOT be reported even if they contain matches."""
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    pkg_profile = tmp_path / ".pkg" / "profiles" / "default"

    # A canonical shard with a miss
    _write_shard(pkg_profile, "chunks", "chk_cc0001", _clean_chunk("chk_cc0001", text="password=IN_SCOPE"))

    # Files in out-of-scope dirs with the same shape
    for excluded in ("runs", "indexes", "secrets"):
        d = pkg_profile / excluded / "xx"
        d.mkdir(parents=True, exist_ok=True)
        (d / "poisoned.json").write_text(json.dumps({"text": "password=OUT_OF_SCOPE"}))

    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(pkg_profile, detectors)

    # Only the chunks/ miss should appear
    assert len(misses) == 1, f"expected exactly one miss from chunks/, got {misses}"
    assert misses[0]["path"].startswith("chunks/")


def test_miss_records_do_not_echo_secret_value(tmp_path: Path):
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    pkg_profile = tmp_path / ".pkg" / "profiles" / "default"
    SENTINEL = "NEVER_ECHOED_SENTINEL_123"
    _write_shard(pkg_profile, "chunks", "chk_dd0002", _clean_chunk("chk_dd0002", text=f"password={SENTINEL}"))

    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(pkg_profile, detectors)

    serialized = json.dumps(misses)
    assert SENTINEL not in serialized


def test_misses_sorted_deterministically(tmp_path: Path):
    """Sort order: path primary, field secondary, category tertiary."""
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    pkg_profile = tmp_path / ".pkg" / "profiles" / "default"
    # Intentionally write in non-sorted order
    _write_shard(pkg_profile, "chunks", "chk_zz9999", _clean_chunk("chk_zz9999", text="password=Z"))
    _write_shard(pkg_profile, "chunks", "chk_aa0001", _clean_chunk("chk_aa0001", text="password=A"))

    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(pkg_profile, detectors)

    paths = [m["path"] for m in misses]
    assert paths == sorted(paths), f"misses not sorted by path: {paths}"


def test_missing_profile_dir_returns_empty(tmp_path: Path):
    """A workspace with no profile directory returns an empty list, not a crash."""
    from auditgraph.query._shard_scanner import scan_shards_for_misses
    from auditgraph.utils.redaction import _default_detectors

    nonexistent = tmp_path / ".pkg" / "profiles" / "nothing"
    detectors = tuple(_default_detectors().values())
    misses = scan_shards_for_misses(nonexistent, detectors)
    assert misses == []
