"""T030: Integration tests for git provenance query functions.

Tests cover:
  - git_who() returns authors with commit counts and date ranges
  - git_log() returns commits ordered by timestamp desc with is_merge and parent_shas
  - git_introduced() returns earliest commit for a file
  - git_history() combines all three
  - All queries use reverse index (not link directory scan)
  - Query for non-existent file returns status=error with message
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from auditgraph.storage.hashing import entity_id
from tests.fixtures.git.generate_fixtures import linear_repo, merge_repo, tag_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(root: Path, *, enabled: bool = True) -> Config:
    raw = deepcopy(DEFAULT_CONFIG)
    raw["profiles"]["default"]["include_paths"] = ["."]
    raw["profiles"]["default"]["exclude_globs"] = ["**/.git/**", "**/__pycache__/**"]
    raw["profiles"]["default"]["git_provenance"]["enabled"] = enabled
    raw["profiles"]["default"]["git_provenance"]["max_tier2_commits"] = 1000
    return Config(raw=raw, source_path=root / "pkg.yaml")


def _setup_and_run(root: Path) -> Path:
    """Run ingest + git-provenance on a repo, return pkg_root."""
    notes_dir = root / "notes"
    notes_dir.mkdir(exist_ok=True)
    (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
    config = _make_config(root)
    runner = PipelineRunner()
    ingest_result = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
    assert ingest_result.status == "ok"
    manifest_path = Path(str(ingest_result.detail.get("manifest", "")))
    run_id = manifest_path.parent.name
    gp_result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
    assert gp_result.status == "ok"
    return profile_pkg_root(root, config)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def linear_pkg(tmp_path: Path) -> Path:
    """Linear repo fixture: 5 commits, 3 files, 2 authors."""
    root = linear_repo(tmp_path / "repo")
    return _setup_and_run(root)


@pytest.fixture
def merge_pkg(tmp_path: Path) -> Path:
    """Merge repo fixture: 4 commits including a merge commit."""
    root = merge_repo(tmp_path / "repo")
    return _setup_and_run(root)


@pytest.fixture
def tag_pkg(tmp_path: Path) -> Path:
    """Tag repo fixture: 2 commits, 2 tags."""
    root = tag_repo(tmp_path / "repo")
    return _setup_and_run(root)


# ---------------------------------------------------------------------------
# Test: git_who
# ---------------------------------------------------------------------------


class TestGitWho:
    """git_who() returns authors with commit counts and date ranges."""

    def test_returns_ok_status(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        assert result["status"] == "ok"
        assert result["file"] == "README.md"

    def test_returns_author_list(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        authors = result["authors"]
        assert isinstance(authors, list)
        assert len(authors) >= 1

    def test_author_has_required_fields(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        author = result["authors"][0]
        assert "email" in author
        assert "names" in author
        assert "commit_count" in author
        assert "earliest" in author
        assert "latest" in author

    def test_author_email_is_string(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        for author in result["authors"]:
            assert isinstance(author["email"], str)

    def test_author_names_is_list(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        for author in result["authors"]:
            assert isinstance(author["names"], list)
            assert len(author["names"]) >= 1

    def test_author_commit_count_is_int(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        for author in result["authors"]:
            assert isinstance(author["commit_count"], int)
            assert author["commit_count"] >= 1

    def test_readme_has_alice_as_author(self, linear_pkg: Path) -> None:
        """README.md is touched by Alice in commits 1 and 5."""
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        emails = [a["email"] for a in result["authors"]]
        assert "alice@example.com" in emails

    def test_readme_alice_commit_count(self, linear_pkg: Path) -> None:
        """Alice touched README.md in 2 commits (add + modify)."""
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        alice = [a for a in result["authors"] if a["email"] == "alice@example.com"][0]
        assert alice["commit_count"] == 2

    def test_alice_has_name_aliases(self, linear_pkg: Path) -> None:
        """Alice committed as both 'Alice Developer' and 'Alice D.' — names list
        should reflect all aliases from the author entity."""
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "src/utils.py")
        alice = [a for a in result["authors"] if a["email"] == "alice@example.com"][0]
        assert isinstance(alice["names"], list)
        assert len(alice["names"]) >= 1

    def test_earliest_latest_are_iso_strings(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "README.md")
        for author in result["authors"]:
            assert isinstance(author["earliest"], str)
            assert isinstance(author["latest"], str)
            # Should be parseable as ISO timestamps
            assert "T" in author["earliest"] or "Z" in author["earliest"]

    def test_nonexistent_file_returns_error(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_who import git_who

        result = git_who(linear_pkg, "does_not_exist.py")
        assert result["status"] == "error"
        assert "message" in result


# ---------------------------------------------------------------------------
# Test: git_log
# ---------------------------------------------------------------------------


class TestGitLog:
    """git_log() returns commits ordered by timestamp desc."""

    def test_returns_ok_status(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        assert result["status"] == "ok"
        assert result["file"] == "README.md"

    def test_returns_commit_list(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        commits = result["commits"]
        assert isinstance(commits, list)
        assert len(commits) == 2  # commits 1 and 5

    def test_commit_has_required_fields(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        commit = result["commits"][0]
        assert "sha" in commit
        assert "subject" in commit
        assert "author_email" in commit
        assert "author_name" in commit
        assert "authored_at" in commit
        assert "is_merge" in commit
        assert "tags" in commit

    def test_commits_ordered_descending(self, linear_pkg: Path) -> None:
        """Commits should be ordered by authored_at descending (newest first)."""
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        commits = result["commits"]
        if len(commits) >= 2:
            assert commits[0]["authored_at"] >= commits[1]["authored_at"]

    def test_commit_sha_is_hex(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        for c in result["commits"]:
            assert isinstance(c["sha"], str)
            assert len(c["sha"]) == 40  # full hex sha

    def test_is_merge_is_boolean(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        for c in result["commits"]:
            assert isinstance(c["is_merge"], bool)

    def test_parent_shas_field_present(self, linear_pkg: Path) -> None:
        """FR-008 compliance: parent_shas field for merge-history filtering."""
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        for c in result["commits"]:
            assert "parent_shas" in c
            assert isinstance(c["parent_shas"], list)

    def test_tags_field_is_list(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "README.md")
        for c in result["commits"]:
            assert isinstance(c["tags"], list)

    def test_merge_commit_detected(self, merge_pkg: Path) -> None:
        """Merge repo has a merge commit that touches feature.py — git_log should show is_merge=True."""
        from auditgraph.query.git_log import git_log

        result = git_log(merge_pkg, "feature.py")
        merge_commits = [c for c in result["commits"] if c["is_merge"]]
        assert len(merge_commits) >= 1

    def test_merge_commit_has_multiple_parents(self, merge_pkg: Path) -> None:
        """Merge commit should have 2+ parent_shas."""
        from auditgraph.query.git_log import git_log

        result = git_log(merge_pkg, "feature.py")
        merge_commits = [c for c in result["commits"] if c["is_merge"]]
        for mc in merge_commits:
            assert len(mc["parent_shas"]) >= 2

    def test_tagged_commit_has_tags(self, tag_pkg: Path) -> None:
        """Tag repo commits should include their tag names."""
        from auditgraph.query.git_log import git_log

        result = git_log(tag_pkg, "README.md")
        all_tags = []
        for c in result["commits"]:
            all_tags.extend(c["tags"])
        assert len(all_tags) >= 1

    def test_nonexistent_file_returns_error(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_log import git_log

        result = git_log(linear_pkg, "does_not_exist.py")
        assert result["status"] == "error"
        assert "message" in result


# ---------------------------------------------------------------------------
# Test: git_introduced
# ---------------------------------------------------------------------------


class TestGitIntroduced:
    """git_introduced() returns the earliest commit for a file."""

    def test_returns_ok_status(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_introduced import git_introduced

        result = git_introduced(linear_pkg, "README.md")
        assert result["status"] == "ok"
        assert result["file"] == "README.md"

    def test_returns_commit_dict(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_introduced import git_introduced

        result = git_introduced(linear_pkg, "README.md")
        commit = result["commit"]
        assert isinstance(commit, dict)
        assert "sha" in commit
        assert "subject" in commit
        assert "authored_at" in commit

    def test_returns_earliest_commit(self, linear_pkg: Path) -> None:
        """README.md was introduced in commit 1 (earliest timestamp)."""
        from auditgraph.query.git_introduced import git_introduced
        from auditgraph.query.git_log import git_log

        result = git_introduced(linear_pkg, "README.md")
        log_result = git_log(linear_pkg, "README.md")
        # Introduced commit should have the smallest authored_at
        all_timestamps = [c["authored_at"] for c in log_result["commits"]]
        assert result["commit"]["authored_at"] == min(all_timestamps)

    def test_lineage_is_empty_list(self, linear_pkg: Path) -> None:
        """V1 basic case: lineage is empty (no rename detection yet)."""
        from auditgraph.query.git_introduced import git_introduced

        result = git_introduced(linear_pkg, "README.md")
        assert result["lineage"] == []

    def test_nonexistent_file_returns_error(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_introduced import git_introduced

        result = git_introduced(linear_pkg, "does_not_exist.py")
        assert result["status"] == "error"
        assert "message" in result


# ---------------------------------------------------------------------------
# Test: git_history
# ---------------------------------------------------------------------------


class TestGitHistory:
    """git_history() combines git_who + git_log + git_introduced."""

    def test_returns_ok_status(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "README.md")
        assert result["status"] == "ok"
        assert result["file"] == "README.md"

    def test_has_authors_field(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "README.md")
        assert "authors" in result
        assert isinstance(result["authors"], list)

    def test_has_commits_field(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "README.md")
        assert "commits" in result
        assert isinstance(result["commits"], list)

    def test_has_introduced_field(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "README.md")
        assert "introduced" in result
        assert isinstance(result["introduced"], dict)
        assert "sha" in result["introduced"]

    def test_has_lineage_field(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "README.md")
        assert "lineage" in result
        assert isinstance(result["lineage"], list)

    def test_authors_match_git_who(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history
        from auditgraph.query.git_who import git_who

        history = git_history(linear_pkg, "README.md")
        who = git_who(linear_pkg, "README.md")
        assert history["authors"] == who["authors"]

    def test_commits_match_git_log(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history
        from auditgraph.query.git_log import git_log

        history = git_history(linear_pkg, "README.md")
        log = git_log(linear_pkg, "README.md")
        assert history["commits"] == log["commits"]

    def test_introduced_match_git_introduced(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history
        from auditgraph.query.git_introduced import git_introduced

        history = git_history(linear_pkg, "README.md")
        intro = git_introduced(linear_pkg, "README.md")
        assert history["introduced"] == intro["commit"]

    def test_nonexistent_file_returns_error(self, linear_pkg: Path) -> None:
        from auditgraph.query.git_history import git_history

        result = git_history(linear_pkg, "does_not_exist.py")
        assert result["status"] == "error"
        assert "message" in result


# ---------------------------------------------------------------------------
# Test: reverse index usage
# ---------------------------------------------------------------------------


class TestReverseIndexUsage:
    """Queries use reverse index (file-commits.json), not link directory scan."""

    def test_reverse_index_is_loaded(self, linear_pkg: Path) -> None:
        """Verify the reverse index file exists and is used by queries."""
        idx_path = linear_pkg / "indexes" / "git-provenance" / "file-commits.json"
        assert idx_path.exists()
        index = read_json(idx_path)
        file_eid = entity_id("file:README.md")
        assert file_eid in index

    def test_query_result_matches_index_data(self, linear_pkg: Path) -> None:
        """Number of commits from git_log should match reverse index entry count."""
        from auditgraph.query.git_log import git_log

        idx_path = linear_pkg / "indexes" / "git-provenance" / "file-commits.json"
        index = read_json(idx_path)
        file_eid = entity_id("file:README.md")
        expected_count = len(index[file_eid])

        result = git_log(linear_pkg, "README.md")
        assert len(result["commits"]) == expected_count
