"""T051: Edge case and robustness tests for Git provenance ingestion.

Tests:
  1. Empty repository (no commits) -> StageResult(status="ok") with zero nodes
  2. Root commit (no parent) -> valid commit node, parent_shas=[], no parent_of link
  3. Non-UTF-8 author name -> handled gracefully via fallback decoding
  4. Missing/corrupted .git directory -> error result, no crash
  5. Large history (100k commits, mocked) -> Tier 2 budget enforced, deterministic
  6. File deleted and never re-added -> modifies links still exist for historical commits
  7. Same file path deleted and re-created in different commits -> no succeeded_from link
  8. git-provenance invoked before run_ingest -> status="missing_manifest"
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.pipeline.runner import PipelineRunner, StageResult
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from tests.fixtures.git.generate_fixtures import (
    delete_recreate_repo,
    encoding_repo,
    linear_repo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(root: Path, *, enabled: bool = True, max_tier2: int = 1000) -> Config:
    """Create a Config with git_provenance enabled."""
    raw = deepcopy(DEFAULT_CONFIG)
    raw["profiles"]["default"]["include_paths"] = ["."]
    raw["profiles"]["default"]["exclude_globs"] = ["**/.git/**", "**/__pycache__/**"]
    raw["profiles"]["default"]["git_provenance"]["enabled"] = enabled
    raw["profiles"]["default"]["git_provenance"]["max_tier2_commits"] = max_tier2
    return Config(raw=raw, source_path=root / "pkg.yaml")


def _run_ingest_then_git_provenance(
    root: Path, config: Config
) -> tuple[StageResult, StageResult, str]:
    """Run ingest first (to create manifest), then git-provenance."""
    runner = PipelineRunner()
    ingest_result = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
    assert ingest_result.status == "ok", f"Ingest failed: {ingest_result.detail}"
    manifest_path = Path(str(ingest_result.detail.get("manifest", "")))
    run_id = manifest_path.parent.name
    gp_result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
    return ingest_result, gp_result, run_id


# ---------------------------------------------------------------------------
# 1. Empty repository (no commits)
# ---------------------------------------------------------------------------


class TestEmptyRepository:
    """Empty repo (init, no commits) produces StageResult ok with zero nodes."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        from dulwich.repo import Repo

        self.root = tmp_path / "empty_repo"
        self.root.mkdir()
        Repo.init(str(self.root))
        # Need a notes file for ingest to succeed
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Empty Repo\n")
        self.config = _make_config(self.root)

    def test_empty_repo_no_crash(self) -> None:
        """Stage completes without exception."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.status == "ok"

    def test_empty_repo_zero_commit_nodes(self) -> None:
        """No commits means zero commit nodes."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.detail["commit_count"] == 0

    def test_empty_repo_zero_author_nodes(self) -> None:
        """No commits means zero author identity nodes."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.detail["author_count"] == 0

    def test_empty_repo_zero_links(self) -> None:
        """No commits means zero links."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.detail["link_count"] == 0


# ---------------------------------------------------------------------------
# 2. Root commit (no parent)
# ---------------------------------------------------------------------------


class TestRootCommit:
    """Root commit produces valid node with parent_shas=[], no parent_of link."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        from dulwich.objects import Blob, Commit, Tree
        from dulwich.repo import Repo

        self.root = tmp_path / "root_commit_repo"
        self.root.mkdir()
        repo = Repo.init(str(self.root))

        blob = Blob.from_string(b"# Root only\n")
        repo.object_store.add_object(blob)
        tree = Tree()
        tree.add(b"README.md", 0o100644, blob.id)
        repo.object_store.add_object(tree)

        commit = Commit()
        commit.tree = tree.id
        commit.author = b"Root Author <root@example.com>"
        commit.committer = b"Root Author <root@example.com>"
        commit.author_time = 1700000000
        commit.author_timezone = 0
        commit.commit_time = 1700000000
        commit.commit_timezone = 0
        commit.encoding = b"UTF-8"
        commit.message = b"Root commit\n"
        commit.parents = []
        repo.object_store.add_object(commit)
        self.commit_sha = commit.id.decode("ascii")

        repo.refs[b"refs/heads/main"] = commit.id
        repo.refs[b"HEAD"] = commit.id
        repo.close()

        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Root\n")
        self.config = _make_config(self.root)

    def test_root_commit_creates_node(self) -> None:
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.status == "ok"
        assert result.detail["commit_count"] == 1

    def test_root_commit_parent_shas_empty(self) -> None:
        """Root commit node has parent_shas=[]."""
        _, result, run_id = _run_ingest_then_git_provenance(self.root, self.config)
        pkg_root = profile_pkg_root(self.root, self.config)

        from auditgraph.storage.hashing import deterministic_commit_id
        from auditgraph.storage.sharding import shard_dir

        repo_path = str(self.root.resolve())
        commit_id = deterministic_commit_id(repo_path, self.commit_sha)
        entity_dir = shard_dir(pkg_root / "entities", commit_id)
        entity_path = entity_dir / f"{commit_id}.json"
        data = read_json(entity_path)
        assert data["parent_shas"] == []

    def test_root_commit_is_merge_false(self) -> None:
        """Root commit is_merge must be false."""
        _, result, run_id = _run_ingest_then_git_provenance(self.root, self.config)
        pkg_root = profile_pkg_root(self.root, self.config)

        from auditgraph.storage.hashing import deterministic_commit_id
        from auditgraph.storage.sharding import shard_dir

        repo_path = str(self.root.resolve())
        commit_id = deterministic_commit_id(repo_path, self.commit_sha)
        entity_dir = shard_dir(pkg_root / "entities", commit_id)
        entity_path = entity_dir / f"{commit_id}.json"
        data = read_json(entity_path)
        assert data["is_merge"] is False

    def test_root_commit_no_parent_of_link(self) -> None:
        """No parent_of links exist for a single root commit."""
        _, result, run_id = _run_ingest_then_git_provenance(self.root, self.config)
        pkg_root = profile_pkg_root(self.root, self.config)

        # Scan all link files in the links directory
        links_dir = pkg_root / "links"
        parent_of_links = []
        if links_dir.exists():
            for shard in links_dir.iterdir():
                if shard.is_dir():
                    for link_file in shard.iterdir():
                        if link_file.suffix == ".json":
                            lnk = read_json(link_file)
                            if lnk.get("type") == "parent_of":
                                parent_of_links.append(lnk)
        assert len(parent_of_links) == 0, f"Expected no parent_of links, found {len(parent_of_links)}"


# ---------------------------------------------------------------------------
# 3. Non-UTF-8 author name
# ---------------------------------------------------------------------------


class TestNonUtf8Author:
    """Non-UTF-8 author name handled gracefully via fallback decoding."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = encoding_repo(tmp_path / "encoding_repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Encoding\n")
        self.config = _make_config(self.root)

    def test_non_utf8_no_crash(self) -> None:
        """Stage completes without crashing on non-UTF-8 author."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.status == "ok"

    def test_non_utf8_commit_node_created(self) -> None:
        """A commit node is created despite non-UTF-8 author."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.detail["commit_count"] >= 1

    def test_non_utf8_author_name_decoded(self) -> None:
        """Author name is decoded via fallback (latin-1), not mojibake or empty."""
        from auditgraph.git.reader import GitReader

        reader = GitReader(self.root)
        commits = reader.walk_commits()
        reader.close()
        assert len(commits) >= 1
        author_name = commits[0].author_name
        # The name should contain the accented characters decoded from latin-1
        assert "Ren" in author_name  # Rene with accent
        assert "ller" in author_name  # Mueller with umlaut
        assert len(author_name) > 0

    def test_non_utf8_author_identity_node_created(self) -> None:
        """An AuthorIdentity node exists for the non-UTF-8 author."""
        _, result, _ = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.detail["author_count"] >= 1


# ---------------------------------------------------------------------------
# 4. Missing/corrupted .git directory
# ---------------------------------------------------------------------------


class TestMissingGitDirectory:
    """Missing .git directory produces error result, no crash."""

    def test_missing_git_dir_returns_error(self, tmp_path: Path) -> None:
        """run_git_provenance on a dir with no .git returns an error status."""
        root = tmp_path / "no_git"
        root.mkdir()
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# No Git\n")
        config = _make_config(root)

        # Run ingest first to create manifest
        runner = PipelineRunner()
        ingest_result = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
        assert ingest_result.status == "ok"
        manifest_path = Path(str(ingest_result.detail.get("manifest", "")))
        run_id = manifest_path.parent.name

        # Now run git-provenance -- should not crash, should return error
        result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
        assert result.status != "ok" or "error" in result.status.lower() or "error" in str(result.detail).lower()
        # Ensure it returned a StageResult, not an exception
        assert isinstance(result, StageResult)

    def test_corrupted_git_dir_returns_error(self, tmp_path: Path) -> None:
        """A .git directory that is actually a file (corrupted) returns error."""
        root = tmp_path / "corrupt_git"
        root.mkdir()
        # Create .git as a file, not a directory
        (root / ".git").write_text("not a real git dir")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Corrupt\n")
        config = _make_config(root)

        runner = PipelineRunner()
        ingest_result = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
        assert ingest_result.status == "ok"
        manifest_path = Path(str(ingest_result.detail.get("manifest", "")))
        run_id = manifest_path.parent.name

        result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
        assert isinstance(result, StageResult)
        # Should indicate an error, not "ok"
        assert result.status != "ok"


# ---------------------------------------------------------------------------
# 5. Large history (100k commits, mocked)
# ---------------------------------------------------------------------------


class TestLargeHistoryMocked:
    """100k commits (mocked) -- Tier 2 budget enforced, output deterministic."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        # Use a minimal real repo for the stage infrastructure,
        # but mock the reader to return 100k commits
        self.root = linear_repo(tmp_path / "large_mock")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Large\n")
        self.max_tier2 = 500
        self.config = _make_config(self.root, max_tier2=self.max_tier2)

    def _make_synthetic_commits(self, count: int):
        """Create a list of synthetic CommitInfo objects."""
        from auditgraph.git.reader import CommitInfo

        commits = []
        for i in range(count):
            commits.append(CommitInfo(
                sha=f"{i:040x}",
                subject=f"Commit {i}",
                author_name="Synth Author",
                author_email="synth@example.com",
                authored_at=f"2024-01-01T{(i % 24):02d}:{(i % 60):02d}:00Z",
                committer_name="Synth Author",
                committer_email="synth@example.com",
                committed_at=f"2024-01-01T{(i % 24):02d}:{(i % 60):02d}:00Z",
                parent_shas=[f"{(i - 1):040x}"] if i > 0 else [],
                is_merge=False,
            ))
        return commits

    def test_budget_enforced_100k(self) -> None:
        """With 100k commits, total selected <= tier1_count + max_tier2_commits."""
        from auditgraph.git.reader import CommitInfo, TagInfo, BranchInfo
        from auditgraph.git.selector import select_commits

        commits = self._make_synthetic_commits(100_000)
        tags: list[TagInfo] = []
        branches = [BranchInfo(name="main", head_sha=commits[-1].sha)]

        def mock_diff_stats(sha: str) -> tuple[int, int]:
            idx = int(sha, 16)
            return (idx % 10 + 1, idx % 400)

        def mock_file_paths(sha: str) -> list[str]:
            idx = int(sha, 16)
            return [f"file_{idx % 100}.py"]

        from auditgraph.git.config import load_git_provenance_config

        profile = self.config.profile()
        profile["git_provenance"]["max_tier2_commits"] = self.max_tier2
        git_config = load_git_provenance_config(profile)

        selected = select_commits(
            commits=commits,
            tags=tags,
            branches=branches,
            diff_stats=mock_diff_stats,
            file_paths=mock_file_paths,
            config=git_config,
        )

        tier1_count = sum(1 for c in selected.commits if c.tier == "structural")
        tier2_count = sum(1 for c in selected.commits if c.tier == "scored")
        total = len(selected.commits)

        assert tier2_count <= self.max_tier2, (
            f"Tier 2 count {tier2_count} exceeds budget {self.max_tier2}"
        )
        assert total == tier1_count + tier2_count
        assert total <= tier1_count + self.max_tier2

    def test_deterministic_output_100k(self) -> None:
        """Two selections on same 100k commits produce identical results."""
        from auditgraph.git.reader import CommitInfo, TagInfo, BranchInfo
        from auditgraph.git.selector import select_commits
        from auditgraph.git.config import load_git_provenance_config

        commits = self._make_synthetic_commits(100_000)
        tags: list[TagInfo] = []
        branches = [BranchInfo(name="main", head_sha=commits[-1].sha)]

        def mock_diff_stats(sha: str) -> tuple[int, int]:
            idx = int(sha, 16)
            return (idx % 10 + 1, idx % 400)

        def mock_file_paths(sha: str) -> list[str]:
            idx = int(sha, 16)
            return [f"file_{idx % 100}.py"]

        profile = self.config.profile()
        profile["git_provenance"]["max_tier2_commits"] = self.max_tier2
        git_config = load_git_provenance_config(profile)

        run1 = select_commits(commits, tags, branches, mock_diff_stats, mock_file_paths, git_config)
        run2 = select_commits(commits, tags, branches, mock_diff_stats, mock_file_paths, git_config)

        shas1 = [c.sha for c in run1.commits]
        shas2 = [c.sha for c in run2.commits]
        assert shas1 == shas2, "Two runs on same input must produce identical output"


# ---------------------------------------------------------------------------
# 6. File deleted and never re-added
# ---------------------------------------------------------------------------


class TestFileDeletedNeverReAdded:
    """Deleted file retains historical modifies links in the graph."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        from dulwich.objects import Blob, Commit, Tree
        from dulwich.repo import Repo
        import stat

        self.root = tmp_path / "deleted_file_repo"
        self.root.mkdir()
        repo = Repo.init(str(self.root))

        # c1: add file.py
        blob1 = Blob.from_string(b"content v1\n")
        repo.object_store.add_object(blob1)
        tree1 = Tree()
        tree1.add(b"README.md", stat.S_IFREG | 0o644, Blob.from_string(b"# Test\n").id)
        repo.object_store.add_object(repo.object_store[tree1.items()[0].sha] if False else Blob.from_string(b"# Test\n"))
        readme_blob = Blob.from_string(b"# Test\n")
        repo.object_store.add_object(readme_blob)
        tree1 = Tree()
        tree1.add(b"README.md", stat.S_IFREG | 0o644, readme_blob.id)
        tree1.add(b"file.py", stat.S_IFREG | 0o644, blob1.id)
        repo.object_store.add_object(tree1)

        c1 = Commit()
        c1.tree = tree1.id
        c1.author = b"Test <test@example.com>"
        c1.committer = b"Test <test@example.com>"
        c1.author_time = 1700000000
        c1.author_timezone = 0
        c1.commit_time = 1700000000
        c1.commit_timezone = 0
        c1.encoding = b"UTF-8"
        c1.message = b"Add file.py\n"
        c1.parents = []
        repo.object_store.add_object(c1)

        # c2: modify file.py
        blob2 = Blob.from_string(b"content v2\n")
        repo.object_store.add_object(blob2)
        tree2 = Tree()
        tree2.add(b"README.md", stat.S_IFREG | 0o644, readme_blob.id)
        tree2.add(b"file.py", stat.S_IFREG | 0o644, blob2.id)
        repo.object_store.add_object(tree2)

        c2 = Commit()
        c2.tree = tree2.id
        c2.author = b"Test <test@example.com>"
        c2.committer = b"Test <test@example.com>"
        c2.author_time = 1700000100
        c2.author_timezone = 0
        c2.commit_time = 1700000100
        c2.commit_timezone = 0
        c2.encoding = b"UTF-8"
        c2.message = b"Modify file.py\n"
        c2.parents = [c1.id]
        repo.object_store.add_object(c2)

        # c3: delete file.py (only README.md remains)
        tree3 = Tree()
        tree3.add(b"README.md", stat.S_IFREG | 0o644, readme_blob.id)
        repo.object_store.add_object(tree3)

        c3 = Commit()
        c3.tree = tree3.id
        c3.author = b"Test <test@example.com>"
        c3.committer = b"Test <test@example.com>"
        c3.author_time = 1700000200
        c3.author_timezone = 0
        c3.commit_time = 1700000200
        c3.commit_timezone = 0
        c3.encoding = b"UTF-8"
        c3.message = b"Delete file.py\n"
        c3.parents = [c2.id]
        repo.object_store.add_object(c3)

        repo.refs[b"refs/heads/main"] = c3.id
        repo.refs[b"HEAD"] = c3.id
        repo.close()

        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Del\n")
        self.config = _make_config(self.root)

    def test_deleted_file_modifies_links_exist(self) -> None:
        """file.py was touched by commits c1, c2, c3 -- modifies links persist."""
        _, result, run_id = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.status == "ok"

        pkg_root = profile_pkg_root(self.root, self.config)
        from auditgraph.storage.hashing import entity_id

        file_entity_id = entity_id("file:file.py")

        # Check reverse index
        idx_path = pkg_root / "indexes" / "git-provenance" / "file-commits.json"
        reverse_idx = read_json(idx_path)
        assert file_entity_id in reverse_idx, (
            f"Deleted file {file_entity_id} should still appear in reverse index"
        )
        # file.py was added (c1), modified (c2), and deleted (c3) = 3 commits
        assert len(reverse_idx[file_entity_id]) >= 2, (
            "Deleted file should have modifies links from historical commits"
        )


# ---------------------------------------------------------------------------
# 7. Same file path deleted and re-created in different commits
# ---------------------------------------------------------------------------


class TestDeleteRecreateNoLineage:
    """File deleted in one commit and re-created in another => no succeeded_from link."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = delete_recreate_repo(tmp_path / "delete_recreate")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Del Recreate\n")
        self.config = _make_config(self.root)

    def test_no_succeeded_from_link(self) -> None:
        """Delete+recreate across separate commits produces no lineage link."""
        _, result, run_id = _run_ingest_then_git_provenance(self.root, self.config)
        assert result.status == "ok"

        pkg_root = profile_pkg_root(self.root, self.config)

        # Scan all links for succeeded_from type
        links_dir = pkg_root / "links"
        lineage_links = []
        if links_dir.exists():
            for shard in links_dir.iterdir():
                if shard.is_dir():
                    for link_file in shard.iterdir():
                        if link_file.suffix == ".json":
                            lnk = read_json(link_file)
                            if lnk.get("type") == "succeeded_from":
                                lineage_links.append(lnk)

        assert len(lineage_links) == 0, (
            f"Expected no succeeded_from links for delete+recreate, found {len(lineage_links)}: "
            f"{lineage_links}"
        )


# ---------------------------------------------------------------------------
# 8. git-provenance invoked before run_ingest
# ---------------------------------------------------------------------------


class TestGitProvenanceBeforeIngest:
    """Running git-provenance without prior ingest returns missing_manifest."""

    def test_missing_manifest_status(self, tmp_path: Path) -> None:
        """No ingest manifest -> status='missing_manifest'."""
        root = linear_repo(tmp_path / "no_ingest")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# No Ingest\n")
        config = _make_config(root)

        runner = PipelineRunner()
        # Do NOT run ingest -- go straight to git-provenance
        result = runner.run_git_provenance(root=root, config=config, run_id=None)
        assert isinstance(result, StageResult)
        assert result.status == "missing_manifest"
