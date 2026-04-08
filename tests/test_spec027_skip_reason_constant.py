"""Spec 027 FR-002 — symlink_refused skip reason constant."""
from __future__ import annotations


def test_symlink_refused_constant_exists_and_value():
    from auditgraph.ingest.policy import SKIP_REASON_SYMLINK_REFUSED

    assert SKIP_REASON_SYMLINK_REFUSED == "symlink_refused"


def test_symlink_refused_distinct_from_existing_reasons():
    from auditgraph.ingest.policy import (
        SKIP_REASON_SYMLINK_REFUSED,
        SKIP_REASON_UNSUPPORTED,
        SKIP_REASON_UNCHANGED,
    )

    reasons = {
        SKIP_REASON_SYMLINK_REFUSED,
        SKIP_REASON_UNSUPPORTED,
        SKIP_REASON_UNCHANGED,
    }
    assert len(reasons) == 3, "skip reason values must all be distinct"
