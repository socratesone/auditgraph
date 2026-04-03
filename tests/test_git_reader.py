"""Tests for dulwich reader adapter (T006).

Tests walk_commits(), diff_stat(), list_tags(), list_branches(),
empty repo handling, and missing .git error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.git.generate_fixtures import (
    basename_match_repo,
    delete_recreate_repo,
    encoding_repo,
    linear_repo,
    merge_repo,
    rename_repo,
    similarity_rename_repo,
    tag_repo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def linear_path(tmp_path: Path) -> Path:
    return linear_repo(tmp_path / "linear")


@pytest.fixture()
def merge_path(tmp_path: Path) -> Path:
    return merge_repo(tmp_path / "merge")


@pytest.fixture()
def tag_path(tmp_path: Path) -> Path:
    return tag_repo(tmp_path / "tag")


@pytest.fixture()
def encoding_path(tmp_path: Path) -> Path:
    return encoding_repo(tmp_path / "encoding")


@pytest.fixture()
def empty_repo_path(tmp_path: Path) -> Path:
    """Create an empty repo (init but no commits)."""
    from dulwich.repo import Repo

    path = tmp_path / "empty"
    path.mkdir()
    Repo.init(str(path))
    return path


# ---------------------------------------------------------------------------
# walk_commits
# ---------------------------------------------------------------------------


class TestWalkCommits:
    def test_yields_all_commits_linear(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        assert len(commits) == 5

    def test_commit_has_sha(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            assert isinstance(c.sha, str)
            assert len(c.sha) == 40

    def test_commit_has_author_name(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        names = {c.author_name for c in commits}
        assert "Alice Developer" in names or "Alice D." in names

    def test_commit_has_author_email(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        emails = {c.author_email for c in commits}
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails

    def test_commit_has_authored_at(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            assert isinstance(c.authored_at, str)
            assert "T" in c.authored_at  # ISO-8601

    def test_commit_has_committer_fields(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            assert hasattr(c, "committer_name")
            assert hasattr(c, "committer_email")
            assert hasattr(c, "committed_at")

    def test_commit_has_subject(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        subjects = {c.subject for c in commits}
        assert "Add README.md" in subjects

    def test_commit_has_parent_shas(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        # Root commit has no parents
        root = [c for c in commits if len(c.parent_shas) == 0]
        assert len(root) == 1

    def test_commit_is_merge_false_for_linear(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            assert c.is_merge is False

    def test_merge_repo_has_merge_commit(self, merge_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(merge_path)
        commits = list(reader.walk_commits())
        merges = [c for c in commits if c.is_merge]
        assert len(merges) == 1
        assert len(merges[0].parent_shas) == 2

    def test_non_utf8_author_handled(self, encoding_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(encoding_path)
        commits = list(reader.walk_commits())
        assert len(commits) == 1
        # Should not crash and should produce a string
        assert isinstance(commits[0].author_name, str)
        assert "Ren" in commits[0].author_name

    def test_multi_paragraph_message_only_first_line(self, linear_path: Path):
        """Subject should be first line only, even if message is multi-line."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            assert "\n" not in c.subject


# ---------------------------------------------------------------------------
# diff_stat
# ---------------------------------------------------------------------------


class TestDiffStat:
    def test_returns_tuple(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        # Pick a non-root commit
        non_root = [c for c in commits if len(c.parent_shas) > 0][0]
        result = reader.diff_stat(non_root.sha)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_files_changed_positive(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        # Commit that adds src/main.py should change at least 1 file
        non_root = [c for c in commits if len(c.parent_shas) > 0]
        any_positive = any(reader.diff_stat(c.sha)[0] > 0 for c in non_root)
        assert any_positive

    def test_root_commit_counts_all_files(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        root = [c for c in commits if len(c.parent_shas) == 0][0]
        files_changed, lines_changed = reader.diff_stat(root.sha)
        assert files_changed >= 1  # at least README.md

    def test_returns_files_and_lines(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = list(reader.walk_commits())
        for c in commits:
            files_changed, lines_changed = reader.diff_stat(c.sha)
            assert isinstance(files_changed, int)
            assert isinstance(lines_changed, int)
            assert files_changed >= 0
            assert lines_changed >= 0


# ---------------------------------------------------------------------------
# list_tags
# ---------------------------------------------------------------------------


class TestListTags:
    def test_returns_list(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        assert isinstance(tags, list)

    def test_finds_both_tags(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        names = {t.name for t in tags}
        assert "v0.1.0" in names
        assert "v1.0.0" in names

    def test_lightweight_tag_type(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        lw = [t for t in tags if t.name == "v0.1.0"][0]
        assert lw.tag_type == "lightweight"

    def test_annotated_tag_type(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        ann = [t for t in tags if t.name == "v1.0.0"][0]
        assert ann.tag_type == "annotated"

    def test_annotated_tag_has_tagger(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        ann = [t for t in tags if t.name == "v1.0.0"][0]
        assert ann.tagger_name is not None
        assert ann.tagger_email is not None

    def test_lightweight_tag_no_tagger(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        lw = [t for t in tags if t.name == "v0.1.0"][0]
        assert lw.tagger_name is None
        assert lw.tagger_email is None

    def test_tag_has_target_sha(self, tag_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(tag_path)
        tags = reader.list_tags()
        for t in tags:
            assert isinstance(t.target_sha, str)
            assert len(t.target_sha) == 40


# ---------------------------------------------------------------------------
# list_branches
# ---------------------------------------------------------------------------


class TestListBranches:
    def test_returns_list(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        branches = reader.list_branches()
        assert isinstance(branches, list)

    def test_finds_main_branch(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        branches = reader.list_branches()
        names = {b.name for b in branches}
        assert "main" in names

    def test_merge_repo_has_two_branches(self, merge_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(merge_path)
        branches = reader.list_branches()
        names = {b.name for b in branches}
        assert "main" in names
        assert "feature" in names

    def test_branch_has_head_sha(self, linear_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        branches = reader.list_branches()
        for b in branches:
            assert isinstance(b.head_sha, str)
            assert len(b.head_sha) == 40


# ---------------------------------------------------------------------------
# Empty repo and error handling
# ---------------------------------------------------------------------------


class TestEmptyRepo:
    def test_walk_commits_returns_empty(self, empty_repo_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(empty_repo_path)
        commits = list(reader.walk_commits())
        assert commits == []

    def test_list_tags_returns_empty(self, empty_repo_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(empty_repo_path)
        tags = reader.list_tags()
        assert tags == []

    def test_list_branches_returns_empty(self, empty_repo_path: Path):
        from auditgraph.git.reader import GitReader

        reader = GitReader(empty_repo_path)
        branches = reader.list_branches()
        assert branches == []


class TestMissingGitDir:
    def test_raises_on_missing_git(self, tmp_path: Path):
        from auditgraph.git.reader import GitReader

        non_repo = tmp_path / "no_git"
        non_repo.mkdir()
        with pytest.raises(Exception):
            GitReader(non_repo)


# ---------------------------------------------------------------------------
# T041: US6 — detect_renames (Phase 9)
# ---------------------------------------------------------------------------


@pytest.fixture()
def rename_path(tmp_path: Path) -> Path:
    return rename_repo(tmp_path / "rename")


@pytest.fixture()
def similarity_rename_path(tmp_path: Path) -> Path:
    return similarity_rename_repo(tmp_path / "similarity")


@pytest.fixture()
def basename_match_path(tmp_path: Path) -> Path:
    return basename_match_repo(tmp_path / "basename")


@pytest.fixture()
def delete_recreate_path(tmp_path: Path) -> Path:
    return delete_recreate_repo(tmp_path / "delete_recreate")


class TestDetectRenames:
    """Verify reader.detect_renames() returns rename pairs with detection method."""

    def test_exact_rename_detected(self, rename_path: Path):
        """Exact rename (git mv) is detected with method 'rename'."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(rename_path)
        commits = reader.walk_commits()
        # Most recent commit is the rename commit
        rename_commit_sha = commits[0].sha
        renames = reader.detect_renames(rename_commit_sha)
        assert len(renames) == 1
        assert renames[0].old_path == "old_name.py"
        assert renames[0].new_path == "new_name.py"

    def test_exact_rename_detection_method(self, rename_path: Path):
        """Exact rename has detection_method='rename'."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].detection_method == "rename"

    def test_exact_rename_confidence_1_0(self, rename_path: Path):
        """Exact rename has confidence 1.0."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].confidence == 1.0

    def test_similarity_rename_detected(self, similarity_rename_path: Path):
        """Similarity-based rename (>70% content) is detected."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(similarity_rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert len(renames) == 1
        assert renames[0].old_path == "utils.py"
        assert renames[0].new_path == "helpers.py"

    def test_similarity_rename_detection_method(self, similarity_rename_path: Path):
        """Similarity rename has detection_method='similarity'."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(similarity_rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].detection_method == "similarity"

    def test_similarity_rename_confidence_0_8(self, similarity_rename_path: Path):
        """Similarity rename has confidence 0.8."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(similarity_rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].confidence == 0.8

    def test_basename_match_detected(self, basename_match_path: Path):
        """Basename match (same filename, different dir, low similarity) is detected."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(basename_match_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert len(renames) == 1
        assert renames[0].old_path == "src/config.py"
        assert renames[0].new_path == "lib/config.py"

    def test_basename_match_detection_method(self, basename_match_path: Path):
        """Basename match has detection_method='basename_match'."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(basename_match_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].detection_method == "basename_match"

    def test_basename_match_confidence_0_6(self, basename_match_path: Path):
        """Basename match has confidence 0.6."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(basename_match_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].confidence == 0.6

    def test_no_rename_returns_empty(self, linear_path: Path):
        """Commit that doesn't rename anything returns empty list."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(linear_path)
        commits = reader.walk_commits()
        # Pick any commit -- linear repo has no renames
        renames = reader.detect_renames(commits[0].sha)
        assert renames == []

    def test_delete_recreate_different_commits_no_rename(self, delete_recreate_path: Path):
        """Delete in one commit + re-create in another does NOT produce rename pairs.

        Each commit is analyzed independently -- the delete commit has no add,
        and the add commit has no delete, so no rename is detected.
        """
        from auditgraph.git.reader import GitReader

        reader = GitReader(delete_recreate_path)
        commits = reader.walk_commits()
        all_renames = []
        for c in commits:
            all_renames.extend(reader.detect_renames(c.sha))
        assert all_renames == []

    def test_rename_pair_has_commit_sha(self, rename_path: Path):
        """Each rename pair includes the commit sha where the rename occurred."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(rename_path)
        commits = reader.walk_commits()
        renames = reader.detect_renames(commits[0].sha)
        assert renames[0].commit_sha == commits[0].sha
