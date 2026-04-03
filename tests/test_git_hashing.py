"""Tests for git ID generation and shard routing (T009).

Tests full hex digest, determinism, uniqueness, shard_dir routing,
and cross-reference consistency with entity_id().
"""

from __future__ import annotations

import pytest

from auditgraph.storage.hashing import (
    deterministic_author_id,
    deterministic_commit_id,
    deterministic_ref_id,
    deterministic_repo_id,
    deterministic_tag_id,
    entity_id,
    sha256_text,
)
from auditgraph.storage.sharding import shard_dir
from pathlib import Path


# ---------------------------------------------------------------------------
# Full 64-char hex digest (no truncation)
# ---------------------------------------------------------------------------


class TestFullHexDigest:
    def test_commit_id_64_hex(self):
        result = deterministic_commit_id("/repo", "abc123")
        hex_part = result[len("commit_"):]
        assert len(hex_part) == 64
        int(hex_part, 16)  # valid hex

    def test_author_id_64_hex(self):
        result = deterministic_author_id("/repo", "dev@test.com")
        hex_part = result[len("author_"):]
        assert len(hex_part) == 64
        int(hex_part, 16)

    def test_tag_id_64_hex(self):
        result = deterministic_tag_id("/repo", "v1.0")
        hex_part = result[len("tag_"):]
        assert len(hex_part) == 64
        int(hex_part, 16)

    def test_repo_id_64_hex(self):
        result = deterministic_repo_id("/repo")
        hex_part = result[len("repo_"):]
        assert len(hex_part) == 64
        int(hex_part, 16)

    def test_ref_id_64_hex(self):
        result = deterministic_ref_id("/repo", "main")
        hex_part = result[len("ref_"):]
        assert len(hex_part) == 64
        int(hex_part, 16)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_commit_id_deterministic(self):
        a = deterministic_commit_id("/repo", "abc")
        b = deterministic_commit_id("/repo", "abc")
        assert a == b

    def test_author_id_deterministic(self):
        a = deterministic_author_id("/repo", "x@y.com")
        b = deterministic_author_id("/repo", "x@y.com")
        assert a == b

    def test_tag_id_deterministic(self):
        a = deterministic_tag_id("/repo", "v2")
        b = deterministic_tag_id("/repo", "v2")
        assert a == b

    def test_repo_id_deterministic(self):
        a = deterministic_repo_id("/repo")
        b = deterministic_repo_id("/repo")
        assert a == b

    def test_ref_id_deterministic(self):
        a = deterministic_ref_id("/repo", "main")
        b = deterministic_ref_id("/repo", "main")
        assert a == b


# ---------------------------------------------------------------------------
# Different inputs produce different IDs
# ---------------------------------------------------------------------------


class TestUniqueness:
    def test_commit_ids_differ(self):
        a = deterministic_commit_id("/repo", "abc")
        b = deterministic_commit_id("/repo", "def")
        assert a != b

    def test_author_ids_differ(self):
        a = deterministic_author_id("/repo", "a@x.com")
        b = deterministic_author_id("/repo", "b@x.com")
        assert a != b

    def test_tag_ids_differ(self):
        a = deterministic_tag_id("/repo", "v1")
        b = deterministic_tag_id("/repo", "v2")
        assert a != b

    def test_repo_ids_differ(self):
        a = deterministic_repo_id("/repo1")
        b = deterministic_repo_id("/repo2")
        assert a != b

    def test_ref_ids_differ(self):
        a = deterministic_ref_id("/repo", "main")
        b = deterministic_ref_id("/repo", "dev")
        assert a != b

    def test_cross_type_differ(self):
        """Same canonical key with different prefix functions should differ."""
        commit = deterministic_commit_id("/repo", "test")
        author = deterministic_author_id("/repo", "test")
        tag = deterministic_tag_id("/repo", "test")
        assert len({commit, author, tag}) == 3


# ---------------------------------------------------------------------------
# shard_dir routing
# ---------------------------------------------------------------------------


class TestShardDirRouting:
    def test_commit_shard(self):
        cid = deterministic_commit_id("/repo", "abc")
        # shard_dir splits on first _ and takes first 2 chars of remainder
        result = shard_dir(Path("/root"), cid)
        hex_part = cid.split("_", 1)[1]
        expected = Path("/root") / hex_part[:2]
        assert result == expected

    def test_author_shard(self):
        aid = deterministic_author_id("/repo", "dev@test.com")
        result = shard_dir(Path("/root"), aid)
        hex_part = aid.split("_", 1)[1]
        expected = Path("/root") / hex_part[:2]
        assert result == expected

    def test_tag_shard(self):
        tid = deterministic_tag_id("/repo", "v1.0")
        result = shard_dir(Path("/root"), tid)
        hex_part = tid.split("_", 1)[1]
        expected = Path("/root") / hex_part[:2]
        assert result == expected

    def test_repo_shard(self):
        rid = deterministic_repo_id("/repo")
        result = shard_dir(Path("/root"), rid)
        hex_part = rid.split("_", 1)[1]
        expected = Path("/root") / hex_part[:2]
        assert result == expected

    def test_ref_shard(self):
        refid = deterministic_ref_id("/repo", "main")
        result = shard_dir(Path("/root"), refid)
        hex_part = refid.split("_", 1)[1]
        expected = Path("/root") / hex_part[:2]
        assert result == expected


# ---------------------------------------------------------------------------
# Cross-reference: entity_id matches materializer file lookup
# ---------------------------------------------------------------------------


class TestCrossReference:
    def test_entity_id_for_file_matches_expected(self):
        """entity_id('file:src/auth.py') is what the materializer should use."""
        file_id = entity_id("file:src/auth.py")
        assert file_id.startswith("ent_")
        hex_part = file_id[len("ent_"):]
        assert len(hex_part) == 64

    def test_entity_id_deterministic(self):
        a = entity_id("file:src/auth.py")
        b = entity_id("file:src/auth.py")
        assert a == b

    def test_entity_id_different_paths_differ(self):
        a = entity_id("file:src/auth.py")
        b = entity_id("file:src/other.py")
        assert a != b

    def test_entity_id_formula(self):
        result = entity_id("file:src/auth.py")
        expected = f"ent_{sha256_text('file:src/auth.py')}"
        assert result == expected
