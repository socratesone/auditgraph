"""Tests for the `name` field on git provenance entities.

Bug: build_commit_nodes() and build_author_nodes() do not set a top-level
`name` field on the entities they produce, even though every other entity
type in the project (file, ag:note, repository, ref, tag) has one. As a
result:

- BM25 search (auditgraph/index/bm25.py:21) reads entity.get("name", "")
  to build the inverted index. Commits and authors are not searchable by
  their human-readable identifier.
- `auditgraph list --type commit --sort name` returns commits in
  ID-tiebreaker order because every commit's name is "".
- `auditgraph node <id>` returns name=None for these entities.

Fix:
  - commit nodes get name = subject (the first line of the commit message)
  - author_identity nodes get name = first alias (or email if no aliases)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest


REPO_PATH = "/tmp/test-repo"


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
    subject: str = "feat: add user authentication",
    author_name: str = "Alice",
    author_email: str = "alice@example.com",
    authored_at: str = "2026-04-01T12:00:00Z",
) -> _SelectedCommit:
    return _SelectedCommit(
        sha=sha,
        subject=subject,
        author_name=author_name,
        author_email=author_email,
        authored_at=authored_at,
        committer_name=author_name,
        committer_email=author_email,
        committed_at=authored_at,
        parent_shas=[],
        is_merge=False,
        tier="scored",
        importance_score=0.5,
        files_changed=[],
    )


# ---------------------------------------------------------------------------
# Commit name field
# ---------------------------------------------------------------------------


class TestCommitNameField:
    def test_commit_node_has_name_field(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_commit()
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert "name" in node, (
            "commit node missing top-level `name` field; this prevents BM25 "
            "indexing and `--sort name` from working on commits"
        )

    def test_commit_name_equals_subject(self):
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_commit(subject="feat: add user authentication")
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["name"] == "feat: add user authentication"

    def test_commit_name_uses_first_line_of_multiline_subject(self):
        """Defensive: even though `subject` is already the first line via
        materializer normalization, name should not include any newline."""
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_commit(subject="fix: handle edge case\n\nLonger description here")
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["name"] == "fix: handle edge case"
        assert "\n" not in node["name"]

    def test_commit_name_preserved_when_subject_is_empty(self):
        """An empty subject should still produce a non-failing name (empty string),
        not raise."""
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_commit(subject="")
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["name"] == ""

    def test_commit_node_keeps_subject_field_too(self):
        """Backwards compat: existing `subject` field must still be present."""
        from auditgraph.git.materializer import build_commit_nodes

        c = _make_commit(subject="docs: update README")
        node = build_commit_nodes([c], REPO_PATH)[0]
        assert node["subject"] == "docs: update README"
        assert node["name"] == "docs: update README"


# ---------------------------------------------------------------------------
# Author name field
# ---------------------------------------------------------------------------


class TestAuthorNameField:
    def test_author_node_has_name_field(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_commit(author_name="Alice", author_email="alice@example.com")
        node = build_author_nodes([c], REPO_PATH)[0]
        assert "name" in node, (
            "author_identity node missing top-level `name` field; this prevents "
            "BM25 indexing and human-readable display of authors"
        )

    def test_author_name_is_first_alias(self):
        from auditgraph.git.materializer import build_author_nodes

        c = _make_commit(author_name="Alice Example", author_email="alice@example.com")
        node = build_author_nodes([c], REPO_PATH)[0]
        assert node["name"] == "Alice Example"

    def test_author_name_uses_first_alias_when_multiple(self):
        """If the same email has multiple name variants, name uses the first
        sorted alias (matching how name_aliases is constructed)."""
        from auditgraph.git.materializer import build_author_nodes

        c1 = _make_commit(author_name="Bob", author_email="bob@example.com")
        c2 = _make_commit(
            sha="b" * 40,
            author_name="Robert",
            author_email="bob@example.com",
        )
        nodes = build_author_nodes([c1, c2], REPO_PATH)
        bob = next(n for n in nodes if n["email"] == "bob@example.com")
        # name_aliases is sorted, so "Bob" comes before "Robert"
        assert bob["name_aliases"] == ["Bob", "Robert"]
        assert bob["name"] == "Bob"

    def test_author_name_falls_back_to_email_when_alias_missing(self):
        """If for some reason name_aliases is empty, name falls back to email
        rather than being empty."""
        from auditgraph.git.materializer import build_author_nodes

        # Force the empty-aliases path by passing a commit with empty author_name
        c = _make_commit(author_name="", author_email="ghost@example.com")
        nodes = build_author_nodes([c], REPO_PATH)
        ghost = next(n for n in nodes if n["email"] == "ghost@example.com")
        # name_aliases will contain just [""], so name = "" or email — we
        # want a fallback to email so the node is at least identifiable
        assert ghost["name"] in ("ghost@example.com", "")
        # Stronger assertion: prefer email when alias is empty
        if "" in ghost["name_aliases"] and len(ghost["name_aliases"]) == 1:
            assert ghost["name"] == "ghost@example.com", (
                "expected fallback to email when author_name is empty"
            )

    def test_author_node_keeps_email_and_aliases(self):
        """Backwards compat: existing fields must still be present."""
        from auditgraph.git.materializer import build_author_nodes

        c = _make_commit(author_name="Carol", author_email="carol@example.com")
        node = build_author_nodes([c], REPO_PATH)[0]
        assert node["email"] == "carol@example.com"
        assert node["name_aliases"] == ["Carol"]
        assert node["name"] == "Carol"
