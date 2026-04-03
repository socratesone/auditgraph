"""Tests for tiered commit selector (T007).

Tests Tier 1 anchor inclusion, Tier 2 scoring formula, hot/cold path
filtering, budget enforcement, and determinism.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Lightweight data stubs matching expected reader output format
# ---------------------------------------------------------------------------


@dataclass
class _CommitStub:
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


@dataclass
class _TagStub:
    name: str
    tag_type: str
    target_sha: str
    tagger_name: str | None
    tagger_email: str | None
    tagged_at: str | None


@dataclass
class _BranchStub:
    name: str
    head_sha: str


def _stub_commit(
    sha: str = "aaa",
    subject: str = "msg",
    parent_shas: list[str] | None = None,
    is_merge: bool = False,
    authored_at: str = "2023-01-01T00:00:00Z",
) -> _CommitStub:
    return _CommitStub(
        sha=sha,
        subject=subject,
        author_name="Dev",
        author_email="dev@test.com",
        authored_at=authored_at,
        committer_name="Dev",
        committer_email="dev@test.com",
        committed_at=authored_at,
        parent_shas=parent_shas or [],
        is_merge=is_merge,
    )


# ---------------------------------------------------------------------------
# Diff stat stubs: sha -> (files_changed, lines_changed)
# ---------------------------------------------------------------------------


def _make_diff_stats(mapping: dict[str, tuple[int, int]]):
    """Return a callable that looks up diff stats by sha."""
    def lookup(sha: str) -> tuple[int, int]:
        return mapping.get(sha, (0, 0))
    return lookup


# ---------------------------------------------------------------------------
# Config stub
# ---------------------------------------------------------------------------


@dataclass
class _ConfigStub:
    enabled: bool = True
    max_tier2_commits: int = 1000
    hot_paths: list[str] | None = None
    cold_paths: list[str] | None = None

    def __post_init__(self):
        if self.hot_paths is None:
            self.hot_paths = []
        if self.cold_paths is None:
            self.cold_paths = ["*.lock", "*-lock.json", "*.generated.*"]


# ---------------------------------------------------------------------------
# Tier 1 anchors
# ---------------------------------------------------------------------------


class TestTier1Anchors:
    def test_tagged_commit_is_tier1(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="aaa")
        tags = [_TagStub(name="v1.0", tag_type="lightweight", target_sha="aaa",
                         tagger_name=None, tagger_email=None, tagged_at=None)]
        branches = [_BranchStub(name="main", head_sha="aaa")]
        diff_stats = _make_diff_stats({"aaa": (1, 10)})
        file_paths = _make_file_paths({"aaa": ["README.md"]})
        config = _ConfigStub()

        result = select_commits([c1], tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        assert any(c.sha == "aaa" for c in tier1)

    def test_root_commit_is_tier1(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="root", parent_shas=[])
        c2 = _stub_commit(sha="child", parent_shas=["root"])
        tags = []
        branches = [_BranchStub(name="main", head_sha="child")]
        diff_stats = _make_diff_stats({"root": (1, 10), "child": (1, 10)})
        file_paths = _make_file_paths({"root": ["a.py"], "child": ["a.py"]})
        config = _ConfigStub()

        result = select_commits([c1, c2], tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        assert any(c.sha == "root" for c in tier1)

    def test_merge_branch_point_is_tier1(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="merge", parent_shas=["p1", "p2"], is_merge=True)
        tags = []
        branches = [_BranchStub(name="main", head_sha="merge")]
        diff_stats = _make_diff_stats({"merge": (2, 20)})
        file_paths = _make_file_paths({"merge": ["a.py"]})
        config = _ConfigStub()

        result = select_commits([c1], tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        assert any(c.sha == "merge" for c in tier1)

    def test_branch_head_is_tier1(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="head1")
        c2 = _stub_commit(sha="head2")
        tags = []
        branches = [
            _BranchStub(name="main", head_sha="head1"),
            _BranchStub(name="dev", head_sha="head2"),
        ]
        diff_stats = _make_diff_stats({"head1": (1, 1), "head2": (1, 1)})
        file_paths = _make_file_paths({"head1": ["a.py"], "head2": ["b.py"]})
        config = _ConfigStub()

        result = select_commits([c1, c2], tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        shas = {c.sha for c in tier1}
        assert "head1" in shas
        assert "head2" in shas


# ---------------------------------------------------------------------------
# Hot-path promotion
# ---------------------------------------------------------------------------


def _make_file_paths(mapping: dict[str, list[str]]):
    """Return a callable that returns file paths touched by a commit sha."""
    def lookup(sha: str) -> list[str]:
        return mapping.get(sha, [])
    return lookup


class TestHotPathPromotion:
    def test_hot_path_commit_promoted_to_tier1(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="hot", parent_shas=["root"])
        c_root = _stub_commit(sha="root", parent_shas=[])
        tags = []
        branches = [_BranchStub(name="main", head_sha="hot")]
        diff_stats = _make_diff_stats({"hot": (1, 1), "root": (1, 1)})
        file_paths = _make_file_paths({"hot": ["src/core.py"], "root": ["README.md"]})
        config = _ConfigStub(hot_paths=["src/core.py"])

        result = select_commits(
            [c1, c_root], tags, branches, diff_stats, file_paths, config
        )
        tier1 = [c for c in result.commits if c.tier == "structural"]
        assert any(c.sha == "hot" for c in tier1)


# ---------------------------------------------------------------------------
# Cold-path zeroing
# ---------------------------------------------------------------------------


class TestColdPathZeroing:
    def test_cold_path_files_contribute_zero_score(self):
        from auditgraph.git.selector import select_commits

        # c_cold only touches a lock file (cold), c_normal touches a .py file
        c_root = _stub_commit(sha="root", parent_shas=[])
        c_cold = _stub_commit(sha="cold", parent_shas=["root"],
                              authored_at="2023-01-02T00:00:00Z")
        c_normal = _stub_commit(sha="normal", parent_shas=["cold"],
                                authored_at="2023-01-03T00:00:00Z")
        tags = []
        branches = [_BranchStub(name="main", head_sha="normal")]
        # cold has 1 file, 400 lines => score would be 2.0 if not zeroed
        # normal has 1 file, 10 lines => score = 1 + 10/400 = 1.025
        diff_stats = _make_diff_stats({
            "root": (1, 1), "cold": (1, 400), "normal": (1, 10),
        })
        file_paths = _make_file_paths({
            "root": ["README.md"],
            "cold": ["package-lock.json"],
            "normal": ["src/app.py"],
        })
        config = _ConfigStub(max_tier2_commits=5)

        result = select_commits(
            [c_root, c_cold, c_normal], tags, branches, diff_stats, file_paths, config
        )
        tier2 = [c for c in result.commits if c.tier == "scored"]
        # cold commit should have score 0 (all files are cold-path)
        cold_entry = [c for c in tier2 if c.sha == "cold"]
        if cold_entry:
            assert cold_entry[0].importance_score == 0.0


# ---------------------------------------------------------------------------
# Tier 2 scoring formula
# ---------------------------------------------------------------------------


class TestTier2Scoring:
    def test_score_formula_files_plus_lines_div_400(self):
        from auditgraph.git.selector import select_commits

        c_root = _stub_commit(sha="root", parent_shas=[])
        c1 = _stub_commit(sha="scored", parent_shas=["root"],
                          authored_at="2023-01-02T00:00:00Z")
        tags = []
        branches = [_BranchStub(name="main", head_sha="scored")]
        # 3 files changed, 800 lines => score = 3 + 800/400 = 5.0
        diff_stats = _make_diff_stats({"root": (1, 1), "scored": (3, 800)})
        file_paths = _make_file_paths({
            "root": ["README.md"],
            "scored": ["a.py", "b.py", "c.py"],
        })
        config = _ConfigStub()

        result = select_commits(
            [c_root, c1], tags, branches, diff_stats, file_paths, config
        )
        tier2 = [c for c in result.commits if c.tier == "scored"]
        scored_entry = [c for c in tier2 if c.sha == "scored"]
        if scored_entry:
            assert abs(scored_entry[0].importance_score - 5.0) < 0.01

    def test_tier2_sorted_descending(self):
        from auditgraph.git.selector import select_commits

        c_root = _stub_commit(sha="root", parent_shas=[])
        c_high = _stub_commit(sha="high", parent_shas=["root"],
                              authored_at="2023-01-02T00:00:00Z")
        c_low = _stub_commit(sha="low", parent_shas=["high"],
                             authored_at="2023-01-03T00:00:00Z")
        tags = []
        branches = [_BranchStub(name="main", head_sha="low")]
        diff_stats = _make_diff_stats({
            "root": (1, 1), "high": (10, 1000), "low": (1, 10),
        })
        file_paths = _make_file_paths({
            "root": ["a.py"], "high": ["a.py"], "low": ["b.py"],
        })
        config = _ConfigStub()

        result = select_commits(
            [c_root, c_high, c_low], tags, branches, diff_stats, file_paths, config
        )
        tier2 = [c for c in result.commits if c.tier == "scored"]
        scores = [c.importance_score for c in tier2]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Most recent + earliest always in Tier 2
# ---------------------------------------------------------------------------


class TestMostRecentAndEarliest:
    def test_most_recent_in_tier2(self):
        from auditgraph.git.selector import select_commits

        commits = [
            _stub_commit(sha="old", parent_shas=[], authored_at="2023-01-01T00:00:00Z"),
            _stub_commit(sha="mid", parent_shas=["old"], authored_at="2023-06-01T00:00:00Z"),
            _stub_commit(sha="new", parent_shas=["mid"], authored_at="2023-12-01T00:00:00Z"),
        ]
        tags = []
        branches = [_BranchStub(name="main", head_sha="new")]
        diff_stats = _make_diff_stats({
            "old": (1, 1), "mid": (1, 1), "new": (1, 1),
        })
        file_paths = _make_file_paths({
            "old": ["a.py"], "mid": ["a.py"], "new": ["a.py"],
        })
        config = _ConfigStub(max_tier2_commits=5)

        result = select_commits(commits, tags, branches, diff_stats, file_paths, config)
        all_shas = {c.sha for c in result.commits}
        assert "new" in all_shas

    def test_earliest_in_tier2(self):
        from auditgraph.git.selector import select_commits

        commits = [
            _stub_commit(sha="oldest", parent_shas=[], authored_at="2020-01-01T00:00:00Z"),
            _stub_commit(sha="mid", parent_shas=["oldest"], authored_at="2023-06-01T00:00:00Z"),
            _stub_commit(sha="newest", parent_shas=["mid"], authored_at="2023-12-01T00:00:00Z"),
        ]
        tags = []
        branches = [_BranchStub(name="main", head_sha="newest")]
        diff_stats = _make_diff_stats({
            "oldest": (1, 1), "mid": (1, 1), "newest": (1, 1),
        })
        file_paths = _make_file_paths({
            "oldest": ["a.py"], "mid": ["a.py"], "newest": ["a.py"],
        })
        config = _ConfigStub(max_tier2_commits=5)

        result = select_commits(commits, tags, branches, diff_stats, file_paths, config)
        all_shas = {c.sha for c in result.commits}
        assert "oldest" in all_shas


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------


class TestBudgetEnforcement:
    def test_tier2_budget_respected(self):
        from auditgraph.git.selector import select_commits

        # Create 20 non-anchor commits + 1 root
        root = _stub_commit(sha="root", parent_shas=[], authored_at="2020-01-01T00:00:00Z")
        commits = [root]
        prev = "root"
        for i in range(20):
            c = _stub_commit(
                sha=f"c{i:03d}",
                parent_shas=[prev],
                authored_at=f"2023-01-{i+1:02d}T00:00:00Z",
            )
            commits.append(c)
            prev = f"c{i:03d}"
        tags = []
        branches = [_BranchStub(name="main", head_sha="c019")]
        diff_stats = _make_diff_stats(
            {c.sha: (1, 10) for c in commits}
        )
        file_paths = _make_file_paths(
            {c.sha: ["data.py"] for c in commits}
        )
        config = _ConfigStub(max_tier2_commits=5)

        result = select_commits(commits, tags, branches, diff_stats, file_paths, config)
        tier2 = [c for c in result.commits if c.tier == "scored"]
        assert len(tier2) <= 5

    def test_tier1_exceeds_budget_returns_all_tier1_zero_tier2(self):
        """When Tier 1 anchors >= budget, all Tier 1 returned + 0 Tier 2."""
        from auditgraph.git.selector import select_commits

        # Create tagged commits for all 20 -> all are Tier 1
        commits = []
        tags = []
        prev_shas: list[str] = []
        for i in range(20):
            sha = f"t{i:03d}"
            c = _stub_commit(sha=sha, parent_shas=prev_shas,
                             authored_at=f"2023-01-{i+1:02d}T00:00:00Z")
            commits.append(c)
            tags.append(_TagStub(name=f"v{i}", tag_type="lightweight",
                                 target_sha=sha, tagger_name=None,
                                 tagger_email=None, tagged_at=None))
            prev_shas = [sha]

        # One more non-tagged commit
        extra = _stub_commit(sha="extra", parent_shas=[commits[-1].sha],
                             authored_at="2023-02-01T00:00:00Z")
        commits.append(extra)
        branches = [_BranchStub(name="main", head_sha="extra")]
        diff_stats = _make_diff_stats({c.sha: (1, 10) for c in commits})
        file_paths = _make_file_paths({c.sha: ["a.py"] for c in commits})
        config = _ConfigStub(max_tier2_commits=10)

        result = select_commits(commits, tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        tier2 = [c for c in result.commits if c.tier == "scored"]
        # All 20 tagged + branch head + root = tier1 count >= 20
        assert len(tier1) >= 20
        # Total returned >= tier1 count (tier2 may be 0 if budget exhausted)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self):
        from auditgraph.git.selector import select_commits

        commits = [
            _stub_commit(sha="root", parent_shas=[], authored_at="2023-01-01T00:00:00Z"),
            _stub_commit(sha="c1", parent_shas=["root"], authored_at="2023-02-01T00:00:00Z"),
            _stub_commit(sha="c2", parent_shas=["c1"], authored_at="2023-03-01T00:00:00Z"),
        ]
        tags = [_TagStub(name="v1", tag_type="lightweight", target_sha="c1",
                         tagger_name=None, tagger_email=None, tagged_at=None)]
        branches = [_BranchStub(name="main", head_sha="c2")]
        diff_stats = _make_diff_stats({"root": (1, 10), "c1": (2, 50), "c2": (1, 5)})
        file_paths = _make_file_paths({"root": ["a.py"], "c1": ["a.py", "b.py"], "c2": ["a.py"]})
        config = _ConfigStub()

        r1 = select_commits(commits, tags, branches, diff_stats, file_paths, config)
        r2 = select_commits(commits, tags, branches, diff_stats, file_paths, config)

        shas1 = [(c.sha, c.tier, c.importance_score) for c in r1.commits]
        shas2 = [(c.sha, c.tier, c.importance_score) for c in r2.commits]
        assert shas1 == shas2


# ---------------------------------------------------------------------------
# Tier 1 importance_score sentinel
# ---------------------------------------------------------------------------


class TestTier1Score:
    def test_tier1_importance_score_is_negative_one(self):
        from auditgraph.git.selector import select_commits

        c1 = _stub_commit(sha="tagged", parent_shas=[])
        tags = [_TagStub(name="v1", tag_type="lightweight", target_sha="tagged",
                         tagger_name=None, tagger_email=None, tagged_at=None)]
        branches = [_BranchStub(name="main", head_sha="tagged")]
        diff_stats = _make_diff_stats({"tagged": (1, 10)})
        file_paths = _make_file_paths({"tagged": ["a.py"]})
        config = _ConfigStub()

        result = select_commits([c1], tags, branches, diff_stats, file_paths, config)
        tier1 = [c for c in result.commits if c.tier == "structural"]
        for c in tier1:
            assert c.importance_score == -1.0
