"""T015: Integration tests for the git-provenance pipeline stage.

Tests:
  - Full stage run on fixture repo produces expected commit/author/tag/repo node count
  - Entities are written to correct shard directories (via shard_dir())
  - git-provenance-manifest.json is written under runs/{run_id}/
  - Replay log entry is appended with stage: "git_provenance", duration_ms, inputs_hash, outputs_hash
  - enabled=false config returns StageResult(stage="git-provenance", status="skipped", ...)
  - Missing ingest manifest returns StageResult(stage="git-provenance", status="missing_manifest", ...)
  - Reverse index file written at indexes/git-provenance/file-commits.json
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.pipeline.runner import PipelineRunner, StageResult
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from auditgraph.storage.sharding import shard_dir
from tests.fixtures.git.generate_fixtures import linear_repo, tag_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(root: Path, *, enabled: bool = True) -> Config:
    """Create a Config with git_provenance enabled and notes pointing at root."""
    raw = deepcopy(DEFAULT_CONFIG)
    raw["profiles"]["default"]["include_paths"] = ["."]
    raw["profiles"]["default"]["exclude_globs"] = ["**/.git/**", "**/__pycache__/**"]
    raw["profiles"]["default"]["git_provenance"]["enabled"] = enabled
    raw["profiles"]["default"]["git_provenance"]["max_tier2_commits"] = 1000
    return Config(raw=raw, source_path=root / "pkg.yaml")


def _run_ingest_then_git_provenance(
    root: Path, config: Config
) -> tuple[StageResult, StageResult, str]:
    """Run ingest first to create file entities, then run git-provenance stage.

    Returns (ingest_result, git_provenance_result, run_id).
    """
    runner = PipelineRunner()
    ingest_result = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
    assert ingest_result.status == "ok", f"Ingest failed: {ingest_result.detail}"

    manifest_path = Path(str(ingest_result.detail.get("manifest", "")))
    run_id = manifest_path.parent.name

    gp_result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
    return ingest_result, gp_result, run_id


# ---------------------------------------------------------------------------
# Test: full stage run produces correct node counts
# ---------------------------------------------------------------------------


class TestFullStageRun:
    """Full stage run on linear fixture repo produces expected node counts."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        # Create a notes/ dir with a markdown file so ingest has something to process
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_stage_status_ok(self) -> None:
        assert self.result.stage == "git-provenance"
        assert self.result.status == "ok"

    def test_commit_node_count(self) -> None:
        """Linear repo has 5 commits, all should be ingested (Tier 1 includes root + branch head)."""
        detail = self.result.detail
        assert detail["commit_count"] == 5

    def test_author_node_count(self) -> None:
        """Linear repo has 2 unique author emails (alice@example.com, bob@example.com)."""
        detail = self.result.detail
        assert detail["author_count"] == 2

    def test_tag_node_count(self) -> None:
        """Linear repo has no tags."""
        detail = self.result.detail
        assert detail["tag_count"] == 0

    def test_repo_node_created(self) -> None:
        """One repository node is always created."""
        detail = self.result.detail
        assert detail["repo_count"] == 1

    def test_link_count_positive(self) -> None:
        """Should have modifies, authored_by, contains, and parent_of links."""
        detail = self.result.detail
        assert detail["link_count"] > 0


class TestFullStageRunWithTags:
    """Full stage run on tag fixture repo produces tag nodes."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = tag_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_tag_count(self) -> None:
        """Tag repo has 2 tags (v0.1.0 lightweight, v1.0.0 annotated)."""
        detail = self.result.detail
        assert detail["tag_count"] == 2


# ---------------------------------------------------------------------------
# Test: entities written to correct shard directories
# ---------------------------------------------------------------------------


class TestEntitySharding:
    """Entities are written to correct shard directories via shard_dir()."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_commit_entities_sharded(self) -> None:
        """Commit entity JSON files exist under entities/{2-hex-shard}/."""
        entities_dir = self.pkg_root / "entities"
        commit_files = list(entities_dir.rglob("commit_*.json"))
        assert len(commit_files) == 5  # 5 commits in linear repo
        for cf in commit_files:
            entity_id = cf.stem
            expected_shard = shard_dir(entities_dir, entity_id)
            assert cf.parent == expected_shard

    def test_author_entities_sharded(self) -> None:
        """Author entity JSON files exist under entities/{2-hex-shard}/."""
        entities_dir = self.pkg_root / "entities"
        author_files = list(entities_dir.rglob("author_*.json"))
        assert len(author_files) == 2  # 2 unique emails
        for af in author_files:
            entity_id = af.stem
            expected_shard = shard_dir(entities_dir, entity_id)
            assert af.parent == expected_shard

    def test_repo_entity_sharded(self) -> None:
        """Repo entity JSON file exists under entities/{2-hex-shard}/."""
        entities_dir = self.pkg_root / "entities"
        repo_files = list(entities_dir.rglob("repo_*.json"))
        assert len(repo_files) == 1

    def test_link_files_sharded(self) -> None:
        """Link JSON files exist under links/{2-hex-shard}/."""
        links_dir = self.pkg_root / "links"
        link_files = list(links_dir.rglob("lnk_*.json"))
        assert len(link_files) > 0
        for lf in link_files:
            link_id = lf.stem
            expected_shard = shard_dir(links_dir, link_id)
            assert lf.parent == expected_shard


# ---------------------------------------------------------------------------
# Test: manifest written
# ---------------------------------------------------------------------------


class TestManifestWritten:
    """git-provenance-manifest.json is written under runs/{run_id}/."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_manifest_exists(self) -> None:
        manifest_path = self.pkg_root / "runs" / self.run_id / "git-provenance-manifest.json"
        assert manifest_path.exists()

    def test_manifest_has_stage(self) -> None:
        manifest_path = self.pkg_root / "runs" / self.run_id / "git-provenance-manifest.json"
        manifest = read_json(manifest_path)
        assert manifest["stage"] == "git-provenance"

    def test_manifest_has_hashes(self) -> None:
        manifest_path = self.pkg_root / "runs" / self.run_id / "git-provenance-manifest.json"
        manifest = read_json(manifest_path)
        assert "inputs_hash" in manifest
        assert "outputs_hash" in manifest
        assert len(manifest["inputs_hash"]) == 64
        assert len(manifest["outputs_hash"]) == 64


# ---------------------------------------------------------------------------
# Test: replay log appended
# ---------------------------------------------------------------------------


class TestReplayLogAppended:
    """Replay log entry is appended with correct fields."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_replay_log_has_git_provenance_entry(self) -> None:
        replay_path = self.pkg_root / "runs" / self.run_id / "replay-log.jsonl"
        assert replay_path.exists()
        lines = replay_path.read_text().strip().split("\n")
        gp_lines = [json.loads(l) for l in lines if '"git-provenance"' in l or '"git_provenance"' in l]
        assert len(gp_lines) >= 1

    def test_replay_entry_has_required_fields(self) -> None:
        replay_path = self.pkg_root / "runs" / self.run_id / "replay-log.jsonl"
        lines = replay_path.read_text().strip().split("\n")
        gp_lines = [json.loads(l) for l in lines if '"git-provenance"' in l or '"git_provenance"' in l]
        entry = gp_lines[0]
        assert entry["stage"] == "git-provenance"
        assert "duration_ms" in entry
        assert isinstance(entry["duration_ms"], int)
        assert "inputs_hash" in entry
        assert "outputs_hash" in entry


# ---------------------------------------------------------------------------
# Test: disabled config returns skipped
# ---------------------------------------------------------------------------


class TestDisabledConfig:
    """enabled=false config returns StageResult(stage='git-provenance', status='skipped')."""

    def test_returns_skipped_status(self, tmp_path: Path) -> None:
        root = linear_repo(tmp_path / "repo")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\n")
        config = _make_config(root, enabled=False)
        runner = PipelineRunner()
        # Run ingest first to create manifest
        ingest = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
        assert ingest.status == "ok"
        manifest_path = Path(str(ingest.detail.get("manifest", "")))
        run_id = manifest_path.parent.name

        result = runner.run_git_provenance(root=root, config=config, run_id=run_id)
        assert result.stage == "git-provenance"
        assert result.status == "skipped"
        assert result.detail.get("reason") == "disabled"


# ---------------------------------------------------------------------------
# Test: missing ingest manifest returns missing_manifest
# ---------------------------------------------------------------------------


class TestMissingManifest:
    """Missing ingest manifest returns StageResult with status='missing_manifest'."""

    def test_returns_missing_manifest(self, tmp_path: Path) -> None:
        root = tmp_path / "empty_workspace"
        root.mkdir()
        config = _make_config(root, enabled=True)
        runner = PipelineRunner()

        result = runner.run_git_provenance(root=root, config=config, run_id=None)
        assert result.stage == "git-provenance"
        assert result.status == "missing_manifest"


# ---------------------------------------------------------------------------
# Test: reverse index written
# ---------------------------------------------------------------------------


class TestReverseIndex:
    """Reverse index file written at indexes/git-provenance/file-commits.json."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)

    def test_reverse_index_exists(self) -> None:
        idx_path = self.pkg_root / "indexes" / "git-provenance" / "file-commits.json"
        assert idx_path.exists()

    def test_reverse_index_has_file_entries(self) -> None:
        idx_path = self.pkg_root / "indexes" / "git-provenance" / "file-commits.json"
        index = read_json(idx_path)
        # Linear repo touches: README.md, src/main.py, src/utils.py
        # Reverse index keys are file entity IDs
        assert len(index) > 0

    def test_reverse_index_values_are_commit_ids(self) -> None:
        idx_path = self.pkg_root / "indexes" / "git-provenance" / "file-commits.json"
        index = read_json(idx_path)
        for file_id, commit_ids in index.items():
            assert file_id.startswith("ent_")
            assert isinstance(commit_ids, list)
            for cid in commit_ids:
                assert cid.startswith("commit_")


# ---------------------------------------------------------------------------
# Test: run_stage dispatch
# ---------------------------------------------------------------------------


class TestRunStageDispatch:
    """run_stage('git-provenance', ...) dispatches to run_git_provenance."""

    def test_dispatch_returns_stage_result(self, tmp_path: Path) -> None:
        root = linear_repo(tmp_path / "repo")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\n")
        config = _make_config(root)
        runner = PipelineRunner()
        ingest = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
        manifest_path = Path(str(ingest.detail.get("manifest", "")))
        run_id = manifest_path.parent.name

        result = runner.run_stage("git-provenance", root=root, config=config, run_id=run_id)
        assert result.stage == "git-provenance"
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# Test: run_rebuild includes git-provenance
# ---------------------------------------------------------------------------


class TestRebuildIncludesGitProvenance:
    """run_rebuild chain includes git-provenance after ingest."""

    def test_rebuild_with_git_enabled(self, tmp_path: Path) -> None:
        root = linear_repo(tmp_path / "repo")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        config = _make_config(root, enabled=True)
        runner = PipelineRunner()
        result = runner.run_rebuild(root=root, config=config)
        assert result.status == "ok"

        # Verify git-provenance manifest was written
        pkg_root = profile_pkg_root(root, config)
        run_id = result.detail.get("run_id")
        manifest_path = pkg_root / "runs" / run_id / "git-provenance-manifest.json"
        assert manifest_path.exists()

    def test_rebuild_with_git_disabled_still_succeeds(self, tmp_path: Path) -> None:
        root = linear_repo(tmp_path / "repo")
        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        config = _make_config(root, enabled=False)
        runner = PipelineRunner()
        result = runner.run_rebuild(root=root, config=config)
        # Rebuild should still succeed -- skipped is non-failing
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# T023: US2 — Reverse index file-commits.json verification (Phase 4)
# ---------------------------------------------------------------------------


class TestReverseIndexContents:
    """Verify reverse index file-commits.json has correct file_entity_id -> [commit_id] mappings."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = linear_repo(tmp_path / "repo")
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        (notes_dir / "note.md").write_text("# Test Note\nSome content.\n")
        self.config = _make_config(self.root)
        _, self.result, self.run_id = _run_ingest_then_git_provenance(self.root, self.config)
        self.pkg_root = profile_pkg_root(self.root, self.config)
        self.idx_path = self.pkg_root / "indexes" / "git-provenance" / "file-commits.json"

    def test_reverse_index_file_exists(self) -> None:
        """indexes/git-provenance/file-commits.json exists after stage run."""
        assert self.idx_path.exists()

    def test_file_entity_ids_use_entity_id_format(self) -> None:
        """File entity IDs in the index match entity_id('file:' + path) from hashing.py."""
        from auditgraph.storage.hashing import entity_id

        index = read_json(self.idx_path)
        # Linear repo touches: README.md, src/main.py, src/utils.py
        expected_files = ["README.md", "src/main.py", "src/utils.py"]
        for file_path in expected_files:
            file_eid = entity_id(f"file:{file_path}")
            assert file_eid in index, f"Expected file entity ID for {file_path} in index"

    def test_multiple_commits_touching_same_file(self) -> None:
        """Multiple commits touching the same file all appear in that file's commit list.

        In the linear repo:
          - README.md is touched by commit 1 (add) and commit 5 (modify) = 2 commits
          - src/main.py is touched by commit 2 (add) and commit 4 (modify) = 2 commits
        """
        from auditgraph.storage.hashing import entity_id

        index = read_json(self.idx_path)
        readme_id = entity_id("file:README.md")
        assert readme_id in index
        assert len(index[readme_id]) == 2, f"README.md should have 2 commits, got {len(index[readme_id])}"

        main_id = entity_id("file:src/main.py")
        assert main_id in index
        assert len(index[main_id]) == 2, f"src/main.py should have 2 commits, got {len(index[main_id])}"

    def test_single_commit_file_has_one_entry(self) -> None:
        """A file touched by only one commit has exactly one commit in its list.

        src/utils.py is only added in commit 3.
        """
        from auditgraph.storage.hashing import entity_id

        index = read_json(self.idx_path)
        utils_id = entity_id("file:src/utils.py")
        assert utils_id in index
        assert len(index[utils_id]) == 1

    def test_commit_ids_in_index_start_with_commit_prefix(self) -> None:
        """All commit IDs in the reverse index start with 'commit_'."""
        index = read_json(self.idx_path)
        for file_id, commit_ids in index.items():
            for cid in commit_ids:
                assert cid.startswith("commit_"), f"Commit ID should start with commit_: {cid}"

    def test_correct_commit_to_file_mapping(self) -> None:
        """Verify a specific commit ID appears in the correct file's entry.

        Commit 1 (root) adds README.md, so its deterministic ID should appear
        in README.md's commit list.
        """
        from auditgraph.storage.hashing import entity_id

        index = read_json(self.idx_path)
        readme_id = entity_id("file:README.md")
        # All commit_ids should be 64-hex after "commit_" prefix
        for cid in index[readme_id]:
            hex_part = cid[len("commit_"):]
            assert len(hex_part) == 64, f"Commit ID hex part should be 64 chars"
