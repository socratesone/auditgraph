"""Tests for Spec 025: file entity materialization in git provenance.

This test module covers the migration of `file` entity creation from the
deleted `extract.code_symbols.v1` extractor into the git provenance stage.
After Spec 025, the `build_file_nodes` function in
`auditgraph/git/materializer.py` is the sole creator of `file` entities,
and every path referenced by a commit's `files_changed` list becomes a
materialized entity on disk so that `modifies` links resolve for all
file types (not just code).

See the spec's Clarifications for the design decisions:
  - Q1: schema matches existing extract_code_symbols shape (source_path)
  - Q2: symlinks, submodules, and all git paths treated uniformly
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import entity_id
from auditgraph.storage.sharding import shard_dir


# ---------------------------------------------------------------------------
# Unit-test helpers: a minimal _SelectedCommit stub that mirrors the real
# dataclass in auditgraph/git/selector.py. Using a stub keeps the unit tests
# independent of the real commit-walker.
# ---------------------------------------------------------------------------


@dataclass
class _SelectedCommit:
    sha: str
    subject: str
    author_name: str
    author_email: str
    authored_at: str
    committer_name: str
    committer_email: str
    committed_at: str
    parent_shas: list[str]
    is_merge: bool
    tier: str
    importance_score: float
    files_changed: list[str] = field(default_factory=list)


def _make_commit(
    sha: str = "a" * 40,
    files_changed: list[str] | None = None,
) -> _SelectedCommit:
    return _SelectedCommit(
        sha=sha,
        subject="test commit",
        author_name="Alice",
        author_email="alice@example.com",
        authored_at="2026-04-07T12:00:00Z",
        committer_name="Alice",
        committer_email="alice@example.com",
        committed_at="2026-04-07T12:00:00Z",
        parent_shas=[],
        is_merge=False,
        tier="scored",
        importance_score=1.0,
        files_changed=files_changed or [],
    )


REPO_PATH = "/tmp/test-repo"


# ---------------------------------------------------------------------------
# T003 — build_file_nodes creates one entity per distinct path
# ---------------------------------------------------------------------------


class TestBuildFileNodesUnit:
    """Unit tests for build_file_nodes against a list of stubbed commits."""

    def test_creates_one_entity_per_distinct_path(self):
        from auditgraph.git.materializer import build_file_nodes

        commits = [
            _make_commit("a" * 40, files_changed=["README.md", "src/main.py"]),
            _make_commit("b" * 40, files_changed=["docs/guide.md"]),
            _make_commit("c" * 40, files_changed=["config.yaml", "LICENSE"]),
        ]
        nodes = build_file_nodes(commits, REPO_PATH)

        assert len(nodes) == 5, (
            f"expected 5 distinct file entities (README.md, src/main.py, "
            f"docs/guide.md, config.yaml, LICENSE); got {len(nodes)}"
        )

    # T004 — dedupe paths across commits

    def test_dedupes_paths_across_commits(self):
        from auditgraph.git.materializer import build_file_nodes

        # Four commits all touching the same path.
        commits = [
            _make_commit(f"{chr(ord('a') + i) * 40}", files_changed=["foo/bar.md"])
            for i in range(4)
        ]
        nodes = build_file_nodes(commits, REPO_PATH)

        assert len(nodes) == 1, (
            f"expected 1 entity for a path touched by 4 commits; got {len(nodes)}"
        )
        assert nodes[0]["source_path"] == "foo/bar.md"

    # T005 — entity ID matches modifies link target

    def test_entity_id_matches_modifies_link_target(self):
        from auditgraph.git.materializer import build_file_nodes

        # Compute the expected ID independently via the same function
        # that build_links uses for modifies link to_id values.
        expected_id = entity_id("file:auditgraph/extract/ner.py")

        commits = [
            _make_commit(files_changed=["auditgraph/extract/ner.py"])
        ]
        nodes = build_file_nodes(commits, REPO_PATH)

        assert len(nodes) == 1
        assert nodes[0]["id"] == expected_id, (
            f"file entity ID {nodes[0]['id']} does not match the expected "
            f"modifies link target ID {expected_id}. The two code paths must "
            f"derive IDs the same way (both via entity_id('file:<path>'))."
        )

    # T006 — entity has exactly the required fields (no extras)

    def test_entity_has_required_fields(self):
        from auditgraph.git.materializer import build_file_nodes

        commits = [_make_commit(files_changed=["auditgraph/extract/ner.py"])]
        node = build_file_nodes(commits, REPO_PATH)[0]

        expected_keys = {"id", "type", "name", "canonical_key", "source_path"}
        assert set(node.keys()) == expected_keys, (
            f"file entity has unexpected keys. Expected {expected_keys}; "
            f"got {set(node.keys())}. Per Spec 025 clarification Q1, the "
            f"schema must match the existing extract_code_symbols shape "
            f"exactly — no additional fields allowed in v1."
        )
        assert node["type"] == "file"
        assert node["name"] == "ner.py"
        assert node["canonical_key"] == "file:auditgraph/extract/ner.py"
        assert node["source_path"] == "auditgraph/extract/ner.py"

    # T007 — determinism: two calls produce identical output

    def test_is_deterministic(self):
        from auditgraph.git.materializer import build_file_nodes

        commits = [
            _make_commit("a" * 40, files_changed=["zzz.md", "aaa.py", "mmm.txt"]),
            _make_commit("b" * 40, files_changed=["bbb.yml", "nnn.json"]),
        ]
        first = build_file_nodes(commits, REPO_PATH)
        second = build_file_nodes(commits, REPO_PATH)

        assert first == second, (
            "build_file_nodes is not deterministic: two calls with identical "
            "input produced different output lists. The function must sort "
            "its output (by entity ID) before returning to guarantee replay "
            "reproducibility per the project's determinism constraint."
        )

    # T008 — empty commit list returns empty list

    def test_handles_empty_commit_list(self):
        from auditgraph.git.materializer import build_file_nodes

        assert build_file_nodes([], REPO_PATH) == []

    # T009 — paths with no directory (top-level files)

    def test_handles_paths_with_no_directory(self):
        from auditgraph.git.materializer import build_file_nodes

        commits = [_make_commit(files_changed=["README.md", "LICENSE"])]
        nodes = build_file_nodes(commits, REPO_PATH)

        assert len(nodes) == 2
        by_path = {n["source_path"]: n for n in nodes}
        assert by_path["README.md"]["name"] == "README.md"
        assert by_path["LICENSE"]["name"] == "LICENSE"

    # T010 — symlinks/submodules/special paths treated uniformly (Q2)

    def test_handles_symlink_and_submodule_paths_uniformly(self):
        """Per clarification Q2, every path string becomes a file entity with
        the same schema, regardless of whether the underlying git object is a
        regular file, a symlink, or a submodule. The function does not inspect
        filesystem state or git object kinds."""
        from auditgraph.git.materializer import build_file_nodes

        commits = [
            _make_commit(
                files_changed=[
                    "docs/guide.md",           # regular markdown file
                    "notes/shortcut.md",       # could be a symlink
                    "vendor/somelib",          # could be a submodule
                    ".gitignore",              # project-meta
                ]
            )
        ]
        nodes = build_file_nodes(commits, REPO_PATH)

        # All four become entities with identical schemas.
        assert len(nodes) == 4
        paths = {n["source_path"] for n in nodes}
        assert paths == {
            "docs/guide.md",
            "notes/shortcut.md",
            "vendor/somelib",
            ".gitignore",
        }
        for node in nodes:
            assert set(node.keys()) == {
                "id", "type", "name", "canonical_key", "source_path"
            }
            assert node["type"] == "file"


# ---------------------------------------------------------------------------
# Stage-level integration tests
# ---------------------------------------------------------------------------


def _make_config(root: Path, *, enabled: bool = True) -> Config:
    """Create a Config with git_provenance enabled and include_paths = repo root."""
    raw = deepcopy(DEFAULT_CONFIG)
    raw["profiles"]["default"]["include_paths"] = ["."]
    raw["profiles"]["default"]["exclude_globs"] = ["**/.git/**", "**/__pycache__/**"]
    raw["profiles"]["default"]["git_provenance"]["enabled"] = enabled
    raw["profiles"]["default"]["git_provenance"]["max_tier2_commits"] = 1000
    return Config(raw=raw, source_path=root / "pkg.yaml")


def _run_ingest_and_git_provenance(root: Path, config: Config) -> tuple[str, Path]:
    """Run ingest + git_provenance. Returns (run_id, pkg_root)."""
    runner = PipelineRunner()
    ingest = runner.run_ingest(root=root, config=config, enforce_compatibility=False)
    assert ingest.status == "ok", f"ingest failed: {ingest.detail}"

    manifest_path = Path(str(ingest.detail["manifest"]))
    run_id = manifest_path.parent.name

    gp = runner.run_git_provenance(root=root, config=config, run_id=run_id)
    assert gp.status == "ok", f"git_provenance failed: {gp.detail}"

    pkg_root = profile_pkg_root(root, config)
    return run_id, pkg_root


class TestRunGitProvenanceFileEntities:
    """Integration tests that run the real git_provenance stage on a fixture
    repo and verify file entities land on disk at the expected sharded paths."""

    # T011 — run_git_provenance writes file entities to sharded storage

    def test_run_git_provenance_writes_file_entities_to_sharded_storage(self, tmp_path):
        from tests.fixtures.git.generate_fixtures import linear_repo

        repo_path = linear_repo(tmp_path)
        config = _make_config(repo_path)
        run_id, pkg_root = _run_ingest_and_git_provenance(repo_path, config)

        # linear_repo touches 3 distinct paths: README.md, src/main.py, src/utils.py
        expected_paths = ["README.md", "src/main.py", "src/utils.py"]
        for path in expected_paths:
            expected_id = entity_id(f"file:{path}")
            expected_file = shard_dir(pkg_root / "entities", expected_id) / f"{expected_id}.json"
            assert expected_file.exists(), (
                f"file entity for {path} not written to disk at {expected_file}. "
                f"Expected the Spec 025 build_file_nodes to materialize it."
            )
            # Parse and verify the schema
            entity = json.loads(expected_file.read_text())
            assert entity["type"] == "file"
            assert entity["source_path"] == path

    # T012 — outputs_hash changes when file entities change

    def test_run_git_provenance_includes_file_entities_in_outputs_hash(self, tmp_path):
        """If file entities are included in the stage's outputs_hash, adding a
        file to the repository history must change the hash. This protects
        replay reproducibility — a new file = new hash = re-run replays from
        the changed stage."""
        from tests.fixtures.git.generate_fixtures import linear_repo, tag_repo

        # Build two different repos and compare their git-provenance outputs_hash.
        # linear_repo has 3 distinct paths; tag_repo has a different path count.
        repo1 = linear_repo(tmp_path / "repo1")
        config1 = _make_config(repo1)
        run_id1, pkg_root1 = _run_ingest_and_git_provenance(repo1, config1)
        manifest1 = json.loads(
            (pkg_root1 / "runs" / run_id1 / "git-provenance-manifest.json").read_text()
        )

        repo2 = tag_repo(tmp_path / "repo2")
        config2 = _make_config(repo2)
        run_id2, pkg_root2 = _run_ingest_and_git_provenance(repo2, config2)
        manifest2 = json.loads(
            (pkg_root2 / "runs" / run_id2 / "git-provenance-manifest.json").read_text()
        )

        assert manifest1["outputs_hash"] != manifest2["outputs_hash"], (
            "outputs_hash identical across two different repos — the hash is "
            "not distinguishing file entity content. file_nodes should be part "
            "of the all_entities list that feeds outputs_hash."
        )

    # T013 — LOAD-BEARING: every modifies link to_id resolves to a real entity

    def test_modifies_link_targets_resolve_to_real_entities_after_run_git_provenance(self, tmp_path):
        """The core acceptance test for US1. After the stage runs, every
        `modifies` link on disk has a `to_id` that resolves to a file entity
        that also exists on disk. No dangling references allowed."""
        from tests.fixtures.git.generate_fixtures import linear_repo

        repo_path = linear_repo(tmp_path)
        config = _make_config(repo_path)
        run_id, pkg_root = _run_ingest_and_git_provenance(repo_path, config)

        # Walk every link file and inspect modifies-type links
        links_dir = pkg_root / "links"
        assert links_dir.exists(), "no links directory after git_provenance run"

        modifies_count = 0
        for link_file in links_dir.rglob("*.json"):
            link = json.loads(link_file.read_text())
            if link.get("type") != "modifies":
                continue
            modifies_count += 1
            to_id = link["to_id"]
            # Compute the expected on-disk path for the target entity
            target_path = shard_dir(pkg_root / "entities", to_id) / f"{to_id}.json"
            assert target_path.exists(), (
                f"modifies link {link_file.name} points to {to_id} but no "
                f"entity exists at {target_path}. This is the dangling-"
                f"reference bug that Spec 025 is fixing. build_file_nodes "
                f"should materialize an entity for every path in any "
                f"commit's files_changed list."
            )
        assert modifies_count > 0, (
            "no modifies links found — test fixture must produce at least one"
        )
