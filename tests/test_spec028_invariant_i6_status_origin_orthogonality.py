"""Spec-028 Invariant I6 · parse_status / source_origin orthogonality.

From data-model.md §6:

    I6: For every ingest record, parse_status ∈ {ok, failed, skipped} and
    source_origin ∈ {fresh, cached}. parse_status="failed" implies
    source_origin="fresh". source_origin="cached" implies parse_status="ok".

This test file asserts those invariants at the `build_source_record` producer
boundary so no call site can construct an impossible state.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from auditgraph.ingest.sources import build_source_record


@pytest.fixture()
def a_real_file(tmp_path: Path) -> Path:
    path = tmp_path / "notes" / "a.md"
    path.parent.mkdir(parents=True)
    path.write_text("hello\n", encoding="utf-8")
    return path


def test_ok_fresh_is_valid(a_real_file: Path) -> None:
    record, _ = build_source_record(
        a_real_file, root=a_real_file.parent.parent,
        parser_id="text/markdown", parse_status="ok",
        source_origin="fresh",
    )
    assert record.parse_status == "ok"
    assert record.source_origin == "fresh"


def test_ok_cached_is_valid(a_real_file: Path) -> None:
    record, _ = build_source_record(
        a_real_file, root=a_real_file.parent.parent,
        parser_id="text/markdown", parse_status="ok",
        source_origin="cached",
    )
    assert record.parse_status == "ok"
    assert record.source_origin == "cached"


def test_failed_fresh_is_valid(a_real_file: Path) -> None:
    record, _ = build_source_record(
        a_real_file, root=a_real_file.parent.parent,
        parser_id="text/markdown", parse_status="failed",
        source_origin="fresh",
    )
    assert record.parse_status == "failed"
    assert record.source_origin == "fresh"


def test_skipped_fresh_is_valid(a_real_file: Path) -> None:
    """Genuine skips (unsupported extension, symlink refused) are always fresh."""
    record, _ = build_source_record(
        a_real_file, root=a_real_file.parent.parent,
        parser_id="text/unknown", parse_status="skipped",
        source_origin="fresh",
    )
    assert record.parse_status == "skipped"
    assert record.source_origin == "fresh"


def test_failed_cached_is_rejected(a_real_file: Path) -> None:
    """I6: parse_status="failed" implies source_origin="fresh".

    The producer MUST raise when asked to construct the impossible
    failed+cached combination — cache never stores failures.
    """
    with pytest.raises(ValueError, match="failed.*cached|cached.*failed"):
        build_source_record(
            a_real_file, root=a_real_file.parent.parent,
            parser_id="text/markdown", parse_status="failed",
            source_origin="cached",
        )


def test_invalid_source_origin_is_rejected(a_real_file: Path) -> None:
    with pytest.raises(ValueError, match="source_origin"):
        build_source_record(
            a_real_file, root=a_real_file.parent.parent,
            parser_id="text/markdown", parse_status="ok",
            source_origin="bogus",
        )


def test_skipped_cached_is_rejected(a_real_file: Path) -> None:
    """I6 (full): source_origin="cached" ⇒ parse_status="ok".

    A cache hit can only exist for a record that previously parsed
    successfully — there is no cached payload for a skipped file.
    """
    with pytest.raises(ValueError, match="cached.*ok|ok.*cached"):
        build_source_record(
            a_real_file, root=a_real_file.parent.parent,
            parser_id="text/unknown", parse_status="skipped",
            source_origin="cached",
        )


def test_invalid_parse_status_is_rejected(a_real_file: Path) -> None:
    """parse_status MUST be one of {ok, failed, skipped} — no ad-hoc values."""
    with pytest.raises(ValueError, match="parse_status"):
        build_source_record(
            a_real_file, root=a_real_file.parent.parent,
            parser_id="text/markdown", parse_status="pending",
            source_origin="fresh",
        )


def test_empty_parse_status_is_rejected(a_real_file: Path) -> None:
    with pytest.raises(ValueError, match="parse_status"):
        build_source_record(
            a_real_file, root=a_real_file.parent.parent,
            parser_id="text/markdown", parse_status="",
            source_origin="fresh",
        )
