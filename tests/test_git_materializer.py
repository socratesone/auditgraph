"""Tests for materializer (T008).

Tests entity dict structure, link dict structure, cross-references,
reverse index, and ID format conformance.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest


# ---------------------------------------------------------------------------
# Stubs matching reader/selector output formats
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
    tier: str  # "structural" or "scored"
    importance_score: float
    files_changed: list[str]  # file paths touched by this commit


@dataclass
class _TagStub:
    name: str
    tag_type: str
    target_sha: str
    tagger_name: str | None
    tagger_email: str | None
    tagged_at: str | None


REPO_PATH = "/tmp/test-repo"


def _make_selected_commit(
    sha: str = "abc123" * 7 + "ab",  # 40 chars
    subject: str = "Test commit",
    author_name: str = "Alice",
    author_email: str = "alice@test.com",
    authored_at: str = "2023-11-14T22:13:20Z",
    committer_name: str = "Alice",
    committer_email: str = "alice@test.com",
    committed_at: str = "2023-11-14T22:13:20Z",
    parent_shas: list[str] | None = None,
    is_merge: bool = False,
    tier: str = "scored",
    importance_score: float = 1.5,
    files_changed: list[str] | None = None,
) -> _SelectedCommit:
    return _SelectedCommit(
        sha=sha,
        subject=subject,
        author_name=author_name,
        author_email=author_email,
        authored_at=authored_at,
        committer_name=committer_name,
        committer_email=committer_email,
        committed_at=committed_at,
        parent_shas=parent_shas or [],
        is_merge=is_merge,
        tier=tier,
        importance_score=importance_score,
        files_changed=files_changed or [],
    )


# ---------------------------------------------------------------------------
# Commit entity tests
# ---------------------------------------------------------------------------


class TestBuildCommitNodes:
    def test_returns_list_of_dicts(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit()
        nodes = build_commit_nodes([c], REPO_PATH)
        assert isinstance(nodes, list)
        assert len(nodes) == 1
        assert isinstance(nodes[0], dict)

    def test_commit_has_all_fields(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit()
        node = build_commit_nodes([c], REPO_PATH)[0]
        required_fields = {
            "id", "type", "sha", "subject", "author_name", "author_email",
            "authored_at", "is_merge", "parent_shas", "tier", "importance_score",
        }
        assert required_fields.issubset(node.keys())

    def test_commit_type_is_commit(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit()
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["type"] == "commit"

    def test_commit_id_full_64_hex(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit()
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["id"].startswith("commit_")
        hex_part = node["id"][len("commit_"):]
        assert len(hex_part) == 64

    def test_tier1_importance_score_negative_one(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit(tier="structural", importance_score=-1.0)
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["importance_score"] == -1.0
        assert node["tier"] == "structural"

    def test_tier2_importance_score_positive(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit(tier="scored", importance_score=3.5)
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["importance_score"] == 3.5
        assert node["tier"] == "scored"

    def test_committer_null_when_same_as_author(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit(
            author_name="Alice", author_email="a@t.com",
            committer_name="Alice", committer_email="a@t.com",
            authored_at="2023-01-01T00:00:00Z", committed_at="2023-01-01T00:00:00Z",
        )
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node.get("committer_name") is None
        assert node.get("committer_email") is None
        assert node.get("committed_at") is None

    def test_committer_present_when_different(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit(
            author_name="Alice", author_email="a@t.com",
            committer_name="Bob", committer_email="b@t.com",
            authored_at="2023-01-01T00:00:00Z", committed_at="2023-01-02T00:00:00Z",
        )
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["committer_name"] == "Bob"
        assert node["committer_email"] == "b@t.com"

    def test_subject_is_first_line_only(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_selected_commit(subject="First line")
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert "\n" not in node["subject"]


# ---------------------------------------------------------------------------
# AuthorIdentity entity tests
# ---------------------------------------------------------------------------


class TestBuildAuthorNodes:
    def test_returns_list_of_dicts(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_selected_commit(author_name="Alice", author_email="alice@test.com")
        nodes = build_author_nodes([c], REPO_PATH)
        assert isinstance(nodes, list)
        assert len(nodes) == 1

    def test_author_has_email_and_aliases(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_selected_commit(author_name="Alice", author_email="alice@test.com")
        node = build_author_nodes([c], REPO_PATH)[0]
        assert node["email"] == "alice@test.com"
        assert "name_aliases" in node
        assert "Alice" in node["name_aliases"]

    def test_author_id_full_64_hex(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_selected_commit(author_email="alice@test.com")
        node = build_author_nodes([c], REPO_PATH)[0]
        assert node["id"].startswith("author_")
        hex_part = node["id"][len("author_"):]
        assert len(hex_part) == 64

    def test_author_type(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_selected_commit()
        node = build_author_nodes([c], REPO_PATH)[0]
        assert node["type"] == "author_identity"

    def test_same_email_different_names_one_node(self):
        from auditgraph.git.materializer import build_author_nodes

        c1 = _make_selected_commit(sha="a" * 40, author_name="Alice Developer",
                                   author_email="alice@test.com")
        c2 = _make_selected_commit(sha="b" * 40, author_name="Alice D.",
                                   author_email="alice@test.com")
        nodes = build_author_nodes([c1, c2], REPO_PATH)
        alice_nodes = [n for n in nodes if n["email"] == "alice@test.com"]
        assert len(alice_nodes) == 1

    def test_name_aliases_sorted(self):
        from auditgraph.git.materializer import build_author_nodes

        c1 = _make_selected_commit(sha="a" * 40, author_name="Zara",
                                   author_email="zara@test.com")
        c2 = _make_selected_commit(sha="b" * 40, author_name="Alice",
                                   author_email="zara@test.com")
        nodes = build_author_nodes([c1, c2], REPO_PATH)
        node = [n for n in nodes if n["email"] == "zara@test.com"][0]
        assert node["name_aliases"] == sorted(node["name_aliases"])

    def test_both_names_in_aliases(self):
        from auditgraph.git.materializer import build_author_nodes

        c1 = _make_selected_commit(sha="a" * 40, author_name="Alice Developer",
                                   author_email="alice@test.com")
        c2 = _make_selected_commit(sha="b" * 40, author_name="Alice D.",
                                   author_email="alice@test.com")
        nodes = build_author_nodes([c1, c2], REPO_PATH)
        node = [n for n in nodes if n["email"] == "alice@test.com"][0]
        assert "Alice D." in node["name_aliases"]
        assert "Alice Developer" in node["name_aliases"]


# ---------------------------------------------------------------------------
# Tag entity tests
# ---------------------------------------------------------------------------


class TestBuildTagNodes:
    def test_returns_list_of_dicts(self):
        from auditgraph.git.materializer import build_tag_nodes

        tag = _TagStub(name="v1.0", tag_type="lightweight", target_sha="a" * 40,
                       tagger_name=None, tagger_email=None, tagged_at=None)
        nodes = build_tag_nodes([tag], REPO_PATH)
        assert isinstance(nodes, list)
        assert len(nodes) == 1

    def test_tag_has_all_fields(self):
        from auditgraph.git.materializer import build_tag_nodes

        tag = _TagStub(name="v1.0", tag_type="annotated", target_sha="a" * 40,
                       tagger_name="Bob", tagger_email="bob@t.com",
                       tagged_at="2023-01-01T00:00:00Z")
        node = build_tag_nodes([tag], REPO_PATH)[0]
        assert node["name"] == "v1.0"
        assert node["tag_type"] == "annotated"
        assert node["target_sha"] == "a" * 40
        assert node["tagger_name"] == "Bob"
        assert node["tagger_email"] == "bob@t.com"

    def test_tag_id_full_64_hex(self):
        from auditgraph.git.materializer import build_tag_nodes

        tag = _TagStub(name="v1.0", tag_type="lightweight", target_sha="a" * 40,
                       tagger_name=None, tagger_email=None, tagged_at=None)
        node = build_tag_nodes([tag], REPO_PATH)[0]
        assert node["id"].startswith("tag_")
        hex_part = node["id"][len("tag_"):]
        assert len(hex_part) == 64

    def test_tag_type_is_tag(self):
        from auditgraph.git.materializer import build_tag_nodes

        tag = _TagStub(name="v1.0", tag_type="lightweight", target_sha="a" * 40,
                       tagger_name=None, tagger_email=None, tagged_at=None)
        node = build_tag_nodes([tag], REPO_PATH)[0]
        assert node["type"] == "tag"

    def test_lightweight_tag_no_tagger(self):
        from auditgraph.git.materializer import build_tag_nodes

        tag = _TagStub(name="v1.0", tag_type="lightweight", target_sha="a" * 40,
                       tagger_name=None, tagger_email=None, tagged_at=None)
        node = build_tag_nodes([tag], REPO_PATH)[0]
        assert node["tagger_name"] is None
        assert node["tagger_email"] is None
        assert node["tagged_at"] is None


# ---------------------------------------------------------------------------
# Repository entity tests
# ---------------------------------------------------------------------------


class TestBuildRepoNode:
    def test_returns_dict(self):
        from auditgraph.git.materializer import build_repo_node

        node = build_repo_node(REPO_PATH)
        assert isinstance(node, dict)

    def test_repo_has_required_fields(self):
        from auditgraph.git.materializer import build_repo_node

        node = build_repo_node(REPO_PATH)
        assert "id" in node
        assert "type" in node
        assert "path" in node
        assert "name" in node

    def test_repo_type(self):
        from auditgraph.git.materializer import build_repo_node

        node = build_repo_node(REPO_PATH)
        assert node["type"] == "repository"

    def test_repo_id_full_64_hex(self):
        from auditgraph.git.materializer import build_repo_node

        node = build_repo_node(REPO_PATH)
        assert node["id"].startswith("repo_")
        hex_part = node["id"][len("repo_"):]
        assert len(hex_part) == 64


# ---------------------------------------------------------------------------
# Link tests
# ---------------------------------------------------------------------------


class TestBuildLinks:
    def _make_test_data(self):
        """Build a minimal set of commit/author/tag/repo nodes for link testing."""
        from auditgraph.git.materializer import (
            build_author_nodes,
            build_commit_nodes,
            build_repo_node,
            build_tag_nodes,
        )

        parent_sha = "p" * 40
        child_sha = "c" * 40
        parent_commit = _make_selected_commit(
            sha=parent_sha, subject="Parent", parent_shas=[],
            author_name="Alice", author_email="alice@test.com",
            files_changed=["src/main.py"],
        )
        child_commit = _make_selected_commit(
            sha=child_sha, subject="Child", parent_shas=[parent_sha],
            author_name="Alice", author_email="alice@test.com",
            files_changed=["src/main.py", "README.md"],
        )
        tag = _TagStub(name="v1.0", tag_type="lightweight", target_sha=parent_sha,
                       tagger_name=None, tagger_email=None, tagged_at=None)

        commit_nodes = build_commit_nodes([parent_commit, child_commit], REPO_PATH)
        author_nodes = build_author_nodes([parent_commit, child_commit], REPO_PATH)
        tag_nodes = build_tag_nodes([tag], REPO_PATH)
        repo_node = build_repo_node(REPO_PATH)

        return commit_nodes, author_nodes, tag_nodes, repo_node, [parent_commit, child_commit]

    def test_links_are_list_of_dicts(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        assert isinstance(links, list)
        assert all(isinstance(lnk, dict) for lnk in links)

    def test_link_has_required_schema(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        required_keys = {"id", "from_id", "to_id", "type", "rule_id", "confidence", "authority"}
        for lnk in links:
            assert required_keys.issubset(lnk.keys()), f"Missing keys in {lnk}"

    def test_link_id_format(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        for lnk in links:
            assert lnk["id"].startswith("lnk_")
            hex_part = lnk["id"][len("lnk_"):]
            assert len(hex_part) == 64

    def test_modifies_links_present(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        assert len(modifies) > 0

    def test_modifies_link_uses_entity_id(self):
        """modifies link to_id should match entity_id('file:' + path)."""
        from auditgraph.git.materializer import build_links
        from auditgraph.storage.hashing import entity_id

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        expected_file_id = entity_id("file:src/main.py")
        to_ids = {lnk["to_id"] for lnk in modifies}
        assert expected_file_id in to_ids

    def test_parent_of_links_present(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        parent_links = [lnk for lnk in links if lnk["type"] == "parent_of"]
        assert len(parent_links) >= 1

    def test_parent_of_rule_id(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        parent_links = [lnk for lnk in links if lnk["type"] == "parent_of"]
        for lnk in parent_links:
            assert lnk["rule_id"] == "link.git_parent.v1"

    def test_authored_by_links_present(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        authored = [lnk for lnk in links if lnk["type"] == "authored_by"]
        assert len(authored) >= 1

    def test_authored_by_rule_id(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        authored = [lnk for lnk in links if lnk["type"] == "authored_by"]
        for lnk in authored:
            assert lnk["rule_id"] == "link.git_authored_by.v1"

    def test_contains_links_present(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        contains = [lnk for lnk in links if lnk["type"] == "contains"]
        assert len(contains) >= 1

    def test_contains_rule_id(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        contains = [lnk for lnk in links if lnk["type"] == "contains"]
        for lnk in contains:
            assert lnk["rule_id"] == "link.git_contains.v1"

    def test_tags_links_present(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        tags_links = [lnk for lnk in links if lnk["type"] == "tags"]
        assert len(tags_links) >= 1

    def test_tags_rule_id(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        tags_links = [lnk for lnk in links if lnk["type"] == "tags"]
        for lnk in tags_links:
            assert lnk["rule_id"] == "link.git_tags.v1"

    def test_all_ids_full_64_hex(self):
        from auditgraph.git.materializer import build_links

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = self._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        for lnk in links:
            # Check link id
            hex_part = lnk["id"][len("lnk_"):]
            assert len(hex_part) == 64, f"Link id truncated: {lnk['id']}"


# ---------------------------------------------------------------------------
# Reverse index tests
# ---------------------------------------------------------------------------


class TestBuildReverseIndex:
    def test_returns_dict(self):
        from auditgraph.git.materializer import build_links, build_reverse_index

        # Minimal data
        commit_nodes, author_nodes, tag_nodes, repo_node, selected = TestBuildLinks()._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        result = build_reverse_index(modifies)
        assert isinstance(result, dict)

    def test_file_maps_to_commit_ids(self):
        from auditgraph.git.materializer import build_links, build_reverse_index
        from auditgraph.storage.hashing import entity_id

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = TestBuildLinks()._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        result = build_reverse_index(modifies)

        file_id = entity_id("file:src/main.py")
        assert file_id in result
        assert isinstance(result[file_id], list)
        assert len(result[file_id]) >= 1

    def test_multiple_commits_for_same_file(self):
        from auditgraph.git.materializer import build_links, build_reverse_index
        from auditgraph.storage.hashing import entity_id

        commit_nodes, author_nodes, tag_nodes, repo_node, selected = TestBuildLinks()._make_test_data()
        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, selected, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        result = build_reverse_index(modifies)

        # src/main.py is touched by both parent and child commits
        file_id = entity_id("file:src/main.py")
        assert len(result[file_id]) == 2


# ---------------------------------------------------------------------------
# T022: US2 — Modifies link verification tests (Phase 4)
# ---------------------------------------------------------------------------


class TestModifiesLinks:
    """Verify modifies links created for EACH file touched by EACH commit."""

    def _make_multi_file_data(self):
        """Build commits touching multiple files."""
        from auditgraph.git.materializer import (
            build_author_nodes,
            build_commit_nodes,
            build_repo_node,
            build_tag_nodes,
            build_links,
        )

        # Commit A touches 3 files
        commit_a = _make_selected_commit(
            sha="a" * 40,
            subject="Add three files",
            files_changed=["src/main.py", "src/utils.py", "README.md"],
        )
        # Commit B touches 1 file (overlapping with A)
        commit_b = _make_selected_commit(
            sha="b" * 40,
            subject="Update main",
            parent_shas=["a" * 40],
            files_changed=["src/main.py"],
        )

        commits = [commit_a, commit_b]
        commit_nodes = build_commit_nodes(commits, REPO_PATH)
        author_nodes = build_author_nodes(commits, REPO_PATH)
        tag_nodes: list = []
        repo_node = build_repo_node(REPO_PATH)

        links = build_links(commit_nodes, author_nodes, tag_nodes, repo_node, commits, REPO_PATH)
        modifies = [lnk for lnk in links if lnk["type"] == "modifies"]
        return modifies, commit_nodes, commits

    def test_commit_touching_3_files_produces_3_modifies_links(self):
        """A commit touching 3 files produces exactly 3 modifies links."""
        from auditgraph.storage.hashing import deterministic_commit_id

        modifies, commit_nodes, commits = self._make_multi_file_data()
        commit_a_id = deterministic_commit_id(REPO_PATH, "a" * 40)
        a_links = [lnk for lnk in modifies if lnk["from_id"] == commit_a_id]
        assert len(a_links) == 3

    def test_each_file_has_modifies_link(self):
        """Each file touched by a commit has a corresponding modifies link."""
        from auditgraph.storage.hashing import entity_id, deterministic_commit_id

        modifies, commit_nodes, commits = self._make_multi_file_data()
        commit_a_id = deterministic_commit_id(REPO_PATH, "a" * 40)
        a_links = [lnk for lnk in modifies if lnk["from_id"] == commit_a_id]
        to_ids = {lnk["to_id"] for lnk in a_links}

        for path in ["src/main.py", "src/utils.py", "README.md"]:
            expected = entity_id(f"file:{path}")
            assert expected in to_ids, f"Missing modifies link for {path}"

    def test_modifies_to_id_matches_entity_id_format(self):
        """modifies link to_id matches entity_id('file:' + relative_path) exactly."""
        from auditgraph.storage.hashing import entity_id

        modifies, _, _ = self._make_multi_file_data()
        # All to_ids should be valid entity_id results
        for lnk in modifies:
            assert lnk["to_id"].startswith("ent_"), f"to_id should start with ent_: {lnk['to_id']}"
            hex_part = lnk["to_id"][len("ent_"):]
            assert len(hex_part) == 64, f"to_id hex part should be 64 chars: {lnk['to_id']}"

    def test_modifies_links_have_correct_rule_id(self):
        """All modifies links use rule_id 'link.git_modifies.v1'."""
        modifies, _, _ = self._make_multi_file_data()
        for lnk in modifies:
            assert lnk["rule_id"] == "link.git_modifies.v1"

    def test_modifies_links_total_count(self):
        """Total modifies links = sum of files touched by all commits (3 + 1 = 4)."""
        modifies, _, _ = self._make_multi_file_data()
        assert len(modifies) == 4

    def test_modifies_links_sharding_compatible(self):
        """Modifies link IDs are valid for shard_dir routing (start with lnk_ + 64 hex)."""
        modifies, _, _ = self._make_multi_file_data()
        for lnk in modifies:
            assert lnk["id"].startswith("lnk_")
            hex_part = lnk["id"][len("lnk_"):]
            assert len(hex_part) == 64


# ---------------------------------------------------------------------------
# T027: US3 — Author identity dedup and authored_by link verification (Phase 5)
# ---------------------------------------------------------------------------


class TestAuthorIdentityDedup:
    """Verify same email with different names produces ONE AuthorIdentity
    with sorted name_aliases, and authored_by links connect correctly."""

    def _make_multi_author_data(self):
        """Two commits from same email but different names, plus one from a different author."""
        from auditgraph.git.materializer import (
            build_author_nodes,
            build_commit_nodes,
            build_repo_node,
            build_links,
        )

        # Same email, two different names
        commit_1 = _make_selected_commit(
            sha="a" * 40,
            author_name="Alice Developer",
            author_email="alice@test.com",
            files_changed=["file1.py"],
        )
        commit_2 = _make_selected_commit(
            sha="b" * 40,
            author_name="Alice D.",
            author_email="alice@test.com",
            parent_shas=["a" * 40],
            files_changed=["file2.py"],
        )
        # Different author entirely
        commit_3 = _make_selected_commit(
            sha="c" * 40,
            author_name="Bob Reviewer",
            author_email="bob@test.com",
            parent_shas=["b" * 40],
            files_changed=["file3.py"],
        )

        commits = [commit_1, commit_2, commit_3]
        commit_nodes = build_commit_nodes(commits, REPO_PATH)
        author_nodes = build_author_nodes(commits, REPO_PATH)
        repo_node = build_repo_node(REPO_PATH)
        links = build_links(commit_nodes, author_nodes, [], repo_node, commits, REPO_PATH)

        return author_nodes, links, commits, commit_nodes

    def test_same_email_different_names_one_node(self):
        """Same email with 2 different author names produces ONE AuthorIdentity node."""
        author_nodes, _, _, _ = self._make_multi_author_data()
        alice_nodes = [n for n in author_nodes if n["email"] == "alice@test.com"]
        assert len(alice_nodes) == 1

    def test_name_aliases_contains_both_names(self):
        """The single AuthorIdentity node's name_aliases contains BOTH names."""
        author_nodes, _, _, _ = self._make_multi_author_data()
        alice = [n for n in author_nodes if n["email"] == "alice@test.com"][0]
        assert "Alice Developer" in alice["name_aliases"]
        assert "Alice D." in alice["name_aliases"]

    def test_name_aliases_sorted_alphabetically(self):
        """name_aliases are sorted alphabetically."""
        author_nodes, _, _, _ = self._make_multi_author_data()
        alice = [n for n in author_nodes if n["email"] == "alice@test.com"][0]
        assert alice["name_aliases"] == sorted(alice["name_aliases"])
        # "Alice D." < "Alice Developer" alphabetically
        assert alice["name_aliases"] == ["Alice D.", "Alice Developer"]

    def test_authored_by_links_connect_each_commit_to_correct_author(self):
        """Each commit has an authored_by link pointing to the correct author by email."""
        from auditgraph.storage.hashing import deterministic_author_id, deterministic_commit_id

        author_nodes, links, commits, commit_nodes = self._make_multi_author_data()
        authored_by = [lnk for lnk in links if lnk["type"] == "authored_by"]

        # All 3 commits should have authored_by links
        assert len(authored_by) == 3

        # Commit 1 (alice@test.com) -> alice author node
        commit_1_id = deterministic_commit_id(REPO_PATH, "a" * 40)
        alice_author_id = deterministic_author_id(REPO_PATH, "alice@test.com")
        c1_links = [lnk for lnk in authored_by if lnk["from_id"] == commit_1_id]
        assert len(c1_links) == 1
        assert c1_links[0]["to_id"] == alice_author_id

        # Commit 2 (alice@test.com, different name) -> SAME alice author node
        commit_2_id = deterministic_commit_id(REPO_PATH, "b" * 40)
        c2_links = [lnk for lnk in authored_by if lnk["from_id"] == commit_2_id]
        assert len(c2_links) == 1
        assert c2_links[0]["to_id"] == alice_author_id

        # Commit 3 (bob@test.com) -> bob author node
        commit_3_id = deterministic_commit_id(REPO_PATH, "c" * 40)
        bob_author_id = deterministic_author_id(REPO_PATH, "bob@test.com")
        c3_links = [lnk for lnk in authored_by if lnk["from_id"] == commit_3_id]
        assert len(c3_links) == 1
        assert c3_links[0]["to_id"] == bob_author_id

    def test_author_id_matches_deterministic_author_id(self):
        """Author node ID matches deterministic_author_id(repo_path, email) exactly."""
        from auditgraph.storage.hashing import deterministic_author_id

        author_nodes, _, _, _ = self._make_multi_author_data()
        alice = [n for n in author_nodes if n["email"] == "alice@test.com"][0]
        expected_id = deterministic_author_id(REPO_PATH, "alice@test.com")
        assert alice["id"] == expected_id

        bob = [n for n in author_nodes if n["email"] == "bob@test.com"][0]
        expected_bob_id = deterministic_author_id(REPO_PATH, "bob@test.com")
        assert bob["id"] == expected_bob_id

    def test_total_author_count(self):
        """Two unique emails produce exactly 2 AuthorIdentity nodes."""
        author_nodes, _, _, _ = self._make_multi_author_data()
        assert len(author_nodes) == 2


# ---------------------------------------------------------------------------
# T037: US4 — Commit Parent and Merge Structure (Phase 7)
# ---------------------------------------------------------------------------


class TestParentOfLinksAndMergeStructure:
    """Verify parent_of links for linear history and multi-parent merges,
    and is_merge flag on commit entities."""

    def _make_linear_history(self):
        """Build A -> B -> C linear history."""
        from auditgraph.git.materializer import (
            build_commit_nodes,
            build_author_nodes,
            build_repo_node,
            build_links,
        )

        sha_a = "a" * 40
        sha_b = "b" * 40
        sha_c = "c" * 40

        commit_a = _make_selected_commit(
            sha=sha_a, subject="Commit A", parent_shas=[],
            files_changed=["file1.py"],
        )
        commit_b = _make_selected_commit(
            sha=sha_b, subject="Commit B", parent_shas=[sha_a],
            files_changed=["file2.py"],
        )
        commit_c = _make_selected_commit(
            sha=sha_c, subject="Commit C", parent_shas=[sha_b],
            files_changed=["file3.py"],
        )

        commits = [commit_a, commit_b, commit_c]
        commit_nodes = build_commit_nodes(commits, REPO_PATH)
        author_nodes = build_author_nodes(commits, REPO_PATH)
        repo_node = build_repo_node(REPO_PATH)
        links = build_links(commit_nodes, author_nodes, [], repo_node, commits, REPO_PATH)
        parent_links = [lnk for lnk in links if lnk["type"] == "parent_of"]
        return parent_links, commit_nodes, commits

    def _make_merge_history(self):
        """Build history with a merge commit M that has parents P1 and P2.

        Topology:
          P1 -- M (merge)
          P2 --/
        """
        from auditgraph.git.materializer import (
            build_commit_nodes,
            build_author_nodes,
            build_repo_node,
            build_links,
        )

        sha_p1 = "1" * 40
        sha_p2 = "2" * 40
        sha_m = "3" * 40

        commit_p1 = _make_selected_commit(
            sha=sha_p1, subject="Parent 1", parent_shas=[],
            is_merge=False, files_changed=["main.py"],
        )
        commit_p2 = _make_selected_commit(
            sha=sha_p2, subject="Parent 2", parent_shas=[],
            is_merge=False, files_changed=["feature.py"],
        )
        commit_m = _make_selected_commit(
            sha=sha_m, subject="Merge commit", parent_shas=[sha_p1, sha_p2],
            is_merge=True, files_changed=["main.py", "feature.py"],
        )

        commits = [commit_p1, commit_p2, commit_m]
        commit_nodes = build_commit_nodes(commits, REPO_PATH)
        author_nodes = build_author_nodes(commits, REPO_PATH)
        repo_node = build_repo_node(REPO_PATH)
        links = build_links(commit_nodes, author_nodes, [], repo_node, commits, REPO_PATH)
        parent_links = [lnk for lnk in links if lnk["type"] == "parent_of"]
        return parent_links, commit_nodes, commits

    # --- Linear history tests ---

    def test_linear_history_has_parent_of_links(self):
        """Linear A->B->C: B has parent_of to A, C has parent_of to B."""
        parent_links, _, _ = self._make_linear_history()
        # 2 parent_of links: B->A and C->B
        assert len(parent_links) == 2

    def test_linear_b_links_to_a(self):
        """B's parent_of link points to A."""
        from auditgraph.storage.hashing import deterministic_commit_id

        parent_links, _, _ = self._make_linear_history()
        b_id = deterministic_commit_id(REPO_PATH, "b" * 40)
        a_id = deterministic_commit_id(REPO_PATH, "a" * 40)
        b_parent_links = [lnk for lnk in parent_links if lnk["from_id"] == b_id]
        assert len(b_parent_links) == 1
        assert b_parent_links[0]["to_id"] == a_id

    def test_linear_c_links_to_b(self):
        """C's parent_of link points to B."""
        from auditgraph.storage.hashing import deterministic_commit_id

        parent_links, _, _ = self._make_linear_history()
        c_id = deterministic_commit_id(REPO_PATH, "c" * 40)
        b_id = deterministic_commit_id(REPO_PATH, "b" * 40)
        c_parent_links = [lnk for lnk in parent_links if lnk["from_id"] == c_id]
        assert len(c_parent_links) == 1
        assert c_parent_links[0]["to_id"] == b_id

    # --- Merge commit tests ---

    def test_merge_commit_has_two_parent_of_links(self):
        """Merge commit M with parents P1 and P2 has TWO parent_of links."""
        parent_links, _, _ = self._make_merge_history()
        from auditgraph.storage.hashing import deterministic_commit_id

        m_id = deterministic_commit_id(REPO_PATH, "3" * 40)
        m_parent_links = [lnk for lnk in parent_links if lnk["from_id"] == m_id]
        assert len(m_parent_links) == 2

    def test_merge_parent_links_point_to_both_parents(self):
        """Merge commit M's parent_of links point to P1 and P2."""
        from auditgraph.storage.hashing import deterministic_commit_id

        parent_links, _, _ = self._make_merge_history()
        m_id = deterministic_commit_id(REPO_PATH, "3" * 40)
        p1_id = deterministic_commit_id(REPO_PATH, "1" * 40)
        p2_id = deterministic_commit_id(REPO_PATH, "2" * 40)
        m_parent_links = [lnk for lnk in parent_links if lnk["from_id"] == m_id]
        to_ids = {lnk["to_id"] for lnk in m_parent_links}
        assert p1_id in to_ids
        assert p2_id in to_ids

    # --- is_merge flag tests ---

    def test_merge_commit_has_is_merge_true(self):
        """Merge commit entity has is_merge: true."""
        from auditgraph.git.materializer import build_commit_nodes

        commit_m = _make_selected_commit(
            sha="3" * 40, subject="Merge", parent_shas=["1" * 40, "2" * 40],
            is_merge=True,
        )
        nodes = build_commit_nodes([commit_m], REPO_PATH)
        assert nodes[0]["is_merge"] is True

    def test_non_merge_commit_has_is_merge_false(self):
        """Non-merge commit entity has is_merge: false."""
        from auditgraph.git.materializer import build_commit_nodes

        commit = _make_selected_commit(
            sha="a" * 40, subject="Normal", parent_shas=["b" * 40],
            is_merge=False,
        )
        nodes = build_commit_nodes([commit], REPO_PATH)
        assert nodes[0]["is_merge"] is False

    # --- Root commit tests ---

    def test_root_commit_no_parent_of_link(self):
        """Root commit (no parents) creates no parent_of link."""
        parent_links, _, _ = self._make_linear_history()
        from auditgraph.storage.hashing import deterministic_commit_id

        a_id = deterministic_commit_id(REPO_PATH, "a" * 40)
        a_parent_links = [lnk for lnk in parent_links if lnk["from_id"] == a_id]
        assert len(a_parent_links) == 0

    def test_root_commit_has_empty_parent_shas(self):
        """Root commit entity has parent_shas: []."""
        from auditgraph.git.materializer import build_commit_nodes

        root = _make_selected_commit(sha="a" * 40, parent_shas=[])
        nodes = build_commit_nodes([root], REPO_PATH)
        assert nodes[0]["parent_shas"] == []


# ---------------------------------------------------------------------------
# T059: US5 — Branch/Ref Context Capture (Phase 8)
# ---------------------------------------------------------------------------


@dataclass
class _BranchStub:
    """Stub matching reader.BranchInfo output format."""
    name: str
    head_sha: str


class TestRefNodesAndOnBranchLinks:
    """Verify Ref nodes created for branches and on_branch links connect HEAD commit to Ref."""

    def _make_branch_data(self):
        """Build commits with two branches: main (head=sha_c) and feature (head=sha_b)."""
        from auditgraph.git.materializer import (
            build_commit_nodes,
            build_author_nodes,
            build_repo_node,
            build_links,
            build_ref_nodes,
        )

        sha_a = "a" * 40
        sha_b = "b" * 40
        sha_c = "c" * 40

        commit_a = _make_selected_commit(sha=sha_a, subject="A", parent_shas=[], files_changed=["f1.py"])
        commit_b = _make_selected_commit(sha=sha_b, subject="B", parent_shas=[sha_a], files_changed=["f2.py"])
        commit_c = _make_selected_commit(sha=sha_c, subject="C", parent_shas=[sha_a], files_changed=["f3.py"])

        commits = [commit_a, commit_b, commit_c]
        branches = [
            _BranchStub(name="main", head_sha=sha_c),
            _BranchStub(name="feature", head_sha=sha_b),
        ]

        commit_nodes = build_commit_nodes(commits, REPO_PATH)
        author_nodes = build_author_nodes(commits, REPO_PATH)
        repo_node = build_repo_node(REPO_PATH)
        ref_nodes = build_ref_nodes(branches, REPO_PATH)
        links = build_links(
            commit_nodes, author_nodes, [], repo_node, commits, REPO_PATH,
            ref_nodes=ref_nodes, branches=branches,
        )

        return ref_nodes, links, commit_nodes, branches

    def test_ref_node_created_for_each_branch(self):
        """Each named branch produces a Ref node."""
        ref_nodes, _, _, _ = self._make_branch_data()
        assert len(ref_nodes) == 2

    def test_ref_node_has_correct_fields(self):
        """Ref node has id, type, name, ref_type, head_sha."""
        ref_nodes, _, _, _ = self._make_branch_data()
        for node in ref_nodes:
            assert "id" in node
            assert node["type"] == "ref"
            assert "name" in node
            assert "ref_type" in node
            assert "head_sha" in node

    def test_ref_node_id_uses_deterministic_ref_id(self):
        """Ref node ID matches deterministic_ref_id(repo_path, ref_name)."""
        from auditgraph.storage.hashing import deterministic_ref_id

        ref_nodes, _, _, _ = self._make_branch_data()
        main_node = [n for n in ref_nodes if n["name"] == "main"][0]
        expected_id = deterministic_ref_id(REPO_PATH, "main")
        assert main_node["id"] == expected_id

    def test_ref_node_head_sha(self):
        """Ref node head_sha matches the branch HEAD commit sha."""
        ref_nodes, _, _, _ = self._make_branch_data()
        main_node = [n for n in ref_nodes if n["name"] == "main"][0]
        assert main_node["head_sha"] == "c" * 40

        feature_node = [n for n in ref_nodes if n["name"] == "feature"][0]
        assert feature_node["head_sha"] == "b" * 40

    def test_ref_node_ref_type_is_branch(self):
        """Local branches have ref_type='branch'."""
        ref_nodes, _, _, _ = self._make_branch_data()
        for node in ref_nodes:
            assert node["ref_type"] == "branch"

    def test_on_branch_links_created(self):
        """on_branch links connect branch HEAD commit to Ref node."""
        _, links, _, _ = self._make_branch_data()
        on_branch = [lnk for lnk in links if lnk["type"] == "on_branch"]
        assert len(on_branch) == 2

    def test_on_branch_link_from_commit_to_ref(self):
        """on_branch link from_id is HEAD commit, to_id is Ref node."""
        from auditgraph.storage.hashing import deterministic_commit_id, deterministic_ref_id

        _, links, _, _ = self._make_branch_data()
        on_branch = [lnk for lnk in links if lnk["type"] == "on_branch"]

        main_commit_id = deterministic_commit_id(REPO_PATH, "c" * 40)
        main_ref_id = deterministic_ref_id(REPO_PATH, "main")
        main_links = [lnk for lnk in on_branch if lnk["to_id"] == main_ref_id]
        assert len(main_links) == 1
        assert main_links[0]["from_id"] == main_commit_id

    def test_on_branch_rule_id(self):
        """on_branch links use rule_id 'link.git_branch.v1'."""
        _, links, _, _ = self._make_branch_data()
        on_branch = [lnk for lnk in links if lnk["type"] == "on_branch"]
        for lnk in on_branch:
            assert lnk["rule_id"] == "link.git_branch.v1"

    def test_multiple_branches_produce_multiple_ref_nodes(self):
        """Two branches produce two distinct Ref nodes with different IDs."""
        ref_nodes, _, _, _ = self._make_branch_data()
        ids = {n["id"] for n in ref_nodes}
        assert len(ids) == 2


# ---------------------------------------------------------------------------
# T040: US6 — File Lineage Detection (Phase 9)
# ---------------------------------------------------------------------------


@dataclass
class _RenamePair:
    """Stub matching reader.RenamePair output format."""
    old_path: str
    new_path: str
    detection_method: str  # "rename", "similarity", "basename_match"
    confidence: float
    commit_sha: str


class TestLineageLinks:
    """Verify succeeded_from links produced by build_lineage_links()
    for exact renames, similarity-based renames, basename matches,
    and that delete/re-create does NOT produce lineage."""

    def test_exact_rename_produces_succeeded_from_link(self):
        """Exact rename (git mv) produces a succeeded_from link."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="old_name.py",
            new_path="new_name.py",
            detection_method="rename",
            confidence=1.0,
            commit_sha="a" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        succeeded = [lnk for lnk in links if lnk["type"] == "succeeded_from"]
        assert len(succeeded) == 1

    def test_exact_rename_confidence_is_1_0(self):
        """Exact rename link has confidence 1.0."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="old_name.py",
            new_path="new_name.py",
            detection_method="rename",
            confidence=1.0,
            commit_sha="a" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        assert links[0]["confidence"] == 1.0

    def test_similarity_rename_produces_succeeded_from_link(self):
        """Similarity-based rename (>70% match) produces a succeeded_from link."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="utils.py",
            new_path="helpers.py",
            detection_method="similarity",
            confidence=0.8,
            commit_sha="b" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        succeeded = [lnk for lnk in links if lnk["type"] == "succeeded_from"]
        assert len(succeeded) == 1

    def test_similarity_rename_confidence_is_0_8(self):
        """Similarity-based rename link has confidence 0.8."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="utils.py",
            new_path="helpers.py",
            detection_method="similarity",
            confidence=0.8,
            commit_sha="b" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        assert links[0]["confidence"] == 0.8

    def test_basename_match_produces_succeeded_from_link(self):
        """Basename match (same filename, different dir) produces a succeeded_from link."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="src/config.py",
            new_path="lib/config.py",
            detection_method="basename_match",
            confidence=0.6,
            commit_sha="c" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        succeeded = [lnk for lnk in links if lnk["type"] == "succeeded_from"]
        assert len(succeeded) == 1

    def test_basename_match_confidence_is_0_6(self):
        """Basename match link has confidence 0.6."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="src/config.py",
            new_path="lib/config.py",
            detection_method="basename_match",
            confidence=0.6,
            commit_sha="c" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        assert links[0]["confidence"] == 0.6

    def test_no_renames_produces_no_lineage_links(self):
        """Empty renames list produces no lineage links."""
        from auditgraph.git.materializer import build_lineage_links

        links = build_lineage_links([], REPO_PATH)
        assert links == []

    def test_succeeded_from_link_schema(self):
        """succeeded_from link has correct schema: from_id, to_id, type, rule_id, evidence."""
        from auditgraph.git.materializer import build_lineage_links
        from auditgraph.storage.hashing import entity_id as eid

        renames = [_RenamePair(
            old_path="old.py",
            new_path="new.py",
            detection_method="rename",
            confidence=1.0,
            commit_sha="d" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        lnk = links[0]

        # from_id is the NEW file entity (it succeeded FROM the old)
        assert lnk["from_id"] == eid("file:new.py")
        # to_id is the OLD file entity
        assert lnk["to_id"] == eid("file:old.py")
        assert lnk["type"] == "succeeded_from"
        assert lnk["rule_id"] == "link.git_lineage.v1"
        assert lnk["authority"] == "heuristic"
        assert "id" in lnk
        assert lnk["id"].startswith("lnk_")

    def test_succeeded_from_evidence_contains_detection_method(self):
        """succeeded_from link evidence includes detection_method, old_path, new_path, commit_sha."""
        from auditgraph.git.materializer import build_lineage_links

        renames = [_RenamePair(
            old_path="old.py",
            new_path="new.py",
            detection_method="rename",
            confidence=1.0,
            commit_sha="d" * 40,
        )]
        links = build_lineage_links(renames, REPO_PATH)
        evidence = links[0]["evidence"]
        assert isinstance(evidence, list)
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev["detection_method"] == "rename"
        assert ev["old_path"] == "old.py"
        assert ev["new_path"] == "new.py"
        assert ev["commit_sha"] == "d" * 40
