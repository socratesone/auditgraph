from __future__ import annotations

import re

from auditgraph.storage.hashing import deterministic_timestamp


def test_deterministic_timestamp_returns_iso8601() -> None:
    result = deterministic_timestamp("test-seed")
    # Must end with Z and match ISO-8601 pattern
    assert result.endswith("Z")
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result)


def test_deterministic_timestamp_is_stable() -> None:
    a = deterministic_timestamp("hello")
    b = deterministic_timestamp("hello")
    assert a == b


def test_deterministic_timestamp_varies_by_seed() -> None:
    a = deterministic_timestamp("seed-alpha")
    b = deterministic_timestamp("seed-beta")
    assert a != b


def test_deterministic_timestamp_within_range() -> None:
    """Timestamp seconds must be < 10^9 (~2001-09-09)."""
    result = deterministic_timestamp("any-seed")
    from datetime import datetime, timezone

    dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
    epoch_seconds = int(dt.timestamp())
    assert 0 <= epoch_seconds < 10**9
