"""Tests for Phase 1 git-specific hashing functions (T003) and config defaults (T004)."""

from __future__ import annotations

import pytest

from auditgraph.storage.hashing import sha256_text


class TestDeterministicCommitId:
    def test_returns_commit_prefix(self):
        from auditgraph.storage.hashing import deterministic_commit_id

        result = deterministic_commit_id("/repo", "abc123")
        assert result.startswith("commit_")

    def test_uses_full_sha256(self):
        from auditgraph.storage.hashing import deterministic_commit_id

        result = deterministic_commit_id("/repo", "abc123")
        hex_part = result[len("commit_"):]
        assert len(hex_part) == 64

    def test_deterministic(self):
        from auditgraph.storage.hashing import deterministic_commit_id

        a = deterministic_commit_id("/repo", "abc123")
        b = deterministic_commit_id("/repo", "abc123")
        assert a == b

    def test_different_inputs_differ(self):
        from auditgraph.storage.hashing import deterministic_commit_id

        a = deterministic_commit_id("/repo", "abc123")
        b = deterministic_commit_id("/repo", "def456")
        assert a != b

    def test_formula(self):
        from auditgraph.storage.hashing import deterministic_commit_id

        result = deterministic_commit_id("/repo", "abc123")
        expected = f"commit_{sha256_text('/repo:abc123')}"
        assert result == expected


class TestDeterministicAuthorId:
    def test_returns_author_prefix(self):
        from auditgraph.storage.hashing import deterministic_author_id

        result = deterministic_author_id("/repo", "dev@test.com")
        assert result.startswith("author_")

    def test_uses_full_sha256(self):
        from auditgraph.storage.hashing import deterministic_author_id

        result = deterministic_author_id("/repo", "dev@test.com")
        hex_part = result[len("author_"):]
        assert len(hex_part) == 64

    def test_formula(self):
        from auditgraph.storage.hashing import deterministic_author_id

        result = deterministic_author_id("/repo", "dev@test.com")
        expected = f"author_{sha256_text('/repo:dev@test.com')}"
        assert result == expected


class TestDeterministicTagId:
    def test_returns_tag_prefix(self):
        from auditgraph.storage.hashing import deterministic_tag_id

        result = deterministic_tag_id("/repo", "v1.0.0")
        assert result.startswith("tag_")

    def test_uses_full_sha256(self):
        from auditgraph.storage.hashing import deterministic_tag_id

        result = deterministic_tag_id("/repo", "v1.0.0")
        hex_part = result[len("tag_"):]
        assert len(hex_part) == 64

    def test_formula(self):
        from auditgraph.storage.hashing import deterministic_tag_id

        result = deterministic_tag_id("/repo", "v1.0.0")
        expected = f"tag_{sha256_text('/repo:v1.0.0')}"
        assert result == expected


class TestDeterministicRepoId:
    def test_returns_repo_prefix(self):
        from auditgraph.storage.hashing import deterministic_repo_id

        result = deterministic_repo_id("/repo")
        assert result.startswith("repo_")

    def test_uses_full_sha256(self):
        from auditgraph.storage.hashing import deterministic_repo_id

        result = deterministic_repo_id("/repo")
        hex_part = result[len("repo_"):]
        assert len(hex_part) == 64

    def test_formula(self):
        from auditgraph.storage.hashing import deterministic_repo_id

        result = deterministic_repo_id("/repo")
        expected = f"repo_{sha256_text('/repo')}"
        assert result == expected


class TestDeterministicRefId:
    def test_returns_ref_prefix(self):
        from auditgraph.storage.hashing import deterministic_ref_id

        result = deterministic_ref_id("/repo", "main")
        assert result.startswith("ref_")

    def test_uses_full_sha256(self):
        from auditgraph.storage.hashing import deterministic_ref_id

        result = deterministic_ref_id("/repo", "main")
        hex_part = result[len("ref_"):]
        assert len(hex_part) == 64

    def test_formula(self):
        from auditgraph.storage.hashing import deterministic_ref_id

        result = deterministic_ref_id("/repo", "main")
        expected = f"ref_{sha256_text('/repo:main')}"
        assert result == expected


class TestGitProvenanceConfigDefaults:
    def test_git_provenance_key_exists_in_default_profile(self):
        from auditgraph.config import DEFAULT_CONFIG, DEFAULT_PROFILE_NAME

        profile = DEFAULT_CONFIG["profiles"][DEFAULT_PROFILE_NAME]
        assert "git_provenance" in profile

    def test_enabled_defaults_to_false(self):
        from auditgraph.config import DEFAULT_CONFIG, DEFAULT_PROFILE_NAME

        gp = DEFAULT_CONFIG["profiles"][DEFAULT_PROFILE_NAME]["git_provenance"]
        assert gp["enabled"] is False

    def test_max_tier2_commits_default(self):
        from auditgraph.config import DEFAULT_CONFIG, DEFAULT_PROFILE_NAME

        gp = DEFAULT_CONFIG["profiles"][DEFAULT_PROFILE_NAME]["git_provenance"]
        assert gp["max_tier2_commits"] == 1000

    def test_hot_paths_default(self):
        from auditgraph.config import DEFAULT_CONFIG, DEFAULT_PROFILE_NAME

        gp = DEFAULT_CONFIG["profiles"][DEFAULT_PROFILE_NAME]["git_provenance"]
        assert gp["hot_paths"] == []

    def test_cold_paths_default(self):
        from auditgraph.config import DEFAULT_CONFIG, DEFAULT_PROFILE_NAME

        gp = DEFAULT_CONFIG["profiles"][DEFAULT_PROFILE_NAME]["git_provenance"]
        assert gp["cold_paths"] == ["*.lock", "*-lock.json", "*.generated.*"]

    def test_config_profile_returns_git_provenance(self):
        from auditgraph.config import load_config

        config = load_config(None)
        profile = config.profile()
        assert "git_provenance" in profile
        assert profile["git_provenance"]["enabled"] is False
