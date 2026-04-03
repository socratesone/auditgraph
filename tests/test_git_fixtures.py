"""Tests for fixture repo generators (T005)."""

from __future__ import annotations

import pytest
from dulwich.repo import Repo

from tests.fixtures.git.generate_fixtures import (
    encoding_repo,
    hot_cold_repo,
    large_repo,
    linear_repo,
    merge_repo,
    rename_repo,
    tag_repo,
)


class TestLinearRepo:
    def test_creates_valid_repo(self, tmp_path):
        path = linear_repo(tmp_path / "linear")
        repo = Repo(str(path))
        assert repo.head() is not None
        repo.close()

    def test_has_5_commits(self, tmp_path):
        path = linear_repo(tmp_path / "linear")
        repo = Repo(str(path))
        commits = list(repo.get_walker())
        assert len(commits) == 5
        repo.close()

    def test_has_2_unique_author_emails(self, tmp_path):
        path = linear_repo(tmp_path / "linear")
        repo = Repo(str(path))
        emails = set()
        for entry in repo.get_walker():
            # Extract email from "Name <email>" format
            raw = entry.commit.author.decode("utf-8", errors="replace")
            email = raw.split("<")[1].rstrip(">")
            emails.add(email)
        assert len(emails) == 2
        repo.close()

    def test_same_email_has_two_name_variants(self, tmp_path):
        path = linear_repo(tmp_path / "linear")
        repo = Repo(str(path))
        names_by_email: dict[str, set[str]] = {}
        for entry in repo.get_walker():
            raw = entry.commit.author.decode("utf-8", errors="replace")
            name = raw.split(" <")[0]
            email = raw.split("<")[1].rstrip(">")
            names_by_email.setdefault(email, set()).add(name)
        # alice@example.com should have "Alice Developer" and "Alice D."
        assert len(names_by_email["alice@example.com"]) == 2
        repo.close()

    def test_deterministic(self, tmp_path):
        path1 = linear_repo(tmp_path / "linear1")
        path2 = linear_repo(tmp_path / "linear2")
        repo1 = Repo(str(path1))
        repo2 = Repo(str(path2))
        assert repo1.head() == repo2.head()
        repo1.close()
        repo2.close()


class TestMergeRepo:
    def test_has_merge_commit(self, tmp_path):
        path = merge_repo(tmp_path / "merge")
        repo = Repo(str(path))
        head = repo[repo.head()]
        assert len(head.parents) == 2
        repo.close()

    def test_has_two_branches(self, tmp_path):
        path = merge_repo(tmp_path / "merge")
        repo = Repo(str(path))
        branches = [
            ref for ref in repo.refs.keys()
            if ref.startswith(b"refs/heads/")
        ]
        assert len(branches) == 2
        repo.close()

    def test_has_4_commits(self, tmp_path):
        path = merge_repo(tmp_path / "merge")
        repo = Repo(str(path))
        commits = list(repo.get_walker())
        assert len(commits) == 4
        repo.close()


class TestRenameRepo:
    def test_old_file_absent_in_head(self, tmp_path):
        path = rename_repo(tmp_path / "rename")
        repo = Repo(str(path))
        head = repo[repo.head()]
        tree = repo[head.tree]
        names = [item.path.decode() for item in tree.items()]
        assert "old_name.py" not in names
        assert "new_name.py" in names
        repo.close()

    def test_has_2_commits(self, tmp_path):
        path = rename_repo(tmp_path / "rename")
        repo = Repo(str(path))
        commits = list(repo.get_walker())
        assert len(commits) == 2
        repo.close()


class TestTagRepo:
    def test_has_lightweight_tag(self, tmp_path):
        path = tag_repo(tmp_path / "tag")
        repo = Repo(str(path))
        assert b"refs/tags/v0.1.0" in repo.refs.keys()
        # Lightweight tag points directly to a commit
        tag_sha = repo.refs[b"refs/tags/v0.1.0"]
        obj = repo[tag_sha]
        from dulwich.objects import Commit as DCommit
        assert isinstance(obj, DCommit)
        repo.close()

    def test_has_annotated_tag(self, tmp_path):
        path = tag_repo(tmp_path / "tag")
        repo = Repo(str(path))
        assert b"refs/tags/v1.0.0" in repo.refs.keys()
        tag_sha = repo.refs[b"refs/tags/v1.0.0"]
        obj = repo[tag_sha]
        from dulwich.objects import Tag as DTag
        assert isinstance(obj, DTag)
        assert obj.name == b"v1.0.0"
        repo.close()


class TestLargeRepo:
    def test_creates_n_commits(self, tmp_path):
        n = 20
        path = large_repo(tmp_path / "large", num_commits=n)
        repo = Repo(str(path))
        commits = list(repo.get_walker())
        assert len(commits) == n
        repo.close()

    def test_deterministic(self, tmp_path):
        path1 = large_repo(tmp_path / "large1", num_commits=10)
        path2 = large_repo(tmp_path / "large2", num_commits=10)
        repo1 = Repo(str(path1))
        repo2 = Repo(str(path2))
        assert repo1.head() == repo2.head()
        repo1.close()
        repo2.close()


class TestEncodingRepo:
    def test_creates_valid_repo(self, tmp_path):
        path = encoding_repo(tmp_path / "encoding")
        repo = Repo(str(path))
        assert repo.head() is not None
        repo.close()

    def test_author_has_non_utf8_bytes(self, tmp_path):
        path = encoding_repo(tmp_path / "encoding")
        repo = Repo(str(path))
        head = repo[repo.head()]
        # The raw author bytes should contain latin-1 characters
        author_bytes = head.author
        # Should NOT decode cleanly as UTF-8 (contains 0xe9, 0xfc)
        with pytest.raises(UnicodeDecodeError):
            author_bytes.decode("utf-8", errors="strict")
        # Should decode fine as latin-1
        decoded = author_bytes.decode("latin-1")
        assert "Ren" in decoded
        repo.close()


class TestHotColdRepo:
    def test_has_5_commits(self, tmp_path):
        path = hot_cold_repo(tmp_path / "hotcold")
        repo = Repo(str(path))
        commits = list(repo.get_walker())
        assert len(commits) == 5
        repo.close()

    def test_has_cold_path_files(self, tmp_path):
        path = hot_cold_repo(tmp_path / "hotcold")
        repo = Repo(str(path))
        head = repo[repo.head()]
        tree = repo[head.tree]
        # Flatten tree entries (just check top-level has expected dirs/files)
        names = [item.path.decode() for item in tree.items()]
        assert "package-lock.json" in names
        assert "src" in names
        assert "build" in names
        repo.close()

    def test_deterministic(self, tmp_path):
        path1 = hot_cold_repo(tmp_path / "hc1")
        path2 = hot_cold_repo(tmp_path / "hc2")
        repo1 = Repo(str(path1))
        repo2 = Repo(str(path2))
        assert repo1.head() == repo2.head()
        repo1.close()
        repo2.close()
