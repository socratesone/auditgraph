"""Tiered commit selection algorithm for Git provenance ingestion.

Selects commits in two tiers:
  Tier 1 (structural): Always included -- tagged, root, merge, branch heads, hot-path commits.
  Tier 2 (scored): Budget-filled by importance score = files_changed + (lines_changed / 400).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Output data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectedCommit:
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
    importance_score: float  # -1.0 for Tier 1, positive float for Tier 2
    files_changed: list[str]  # file paths touched by this commit


@dataclass(frozen=True)
class SelectedCommits:
    commits: list[SelectedCommit]


# ---------------------------------------------------------------------------
# Core selection
# ---------------------------------------------------------------------------


def select_commits(
    commits: list[Any],
    tags: list[Any],
    branches: list[Any],
    diff_stats: Callable[[str], tuple[int, int]],
    file_paths: Callable[[str], list[str]],
    config: Any,
) -> SelectedCommits:
    """Apply tiered selection to a list of commits.

    Args:
        commits: List of commit objects with sha, parent_shas, is_merge, authored_at fields.
        tags: List of tag objects with target_sha field.
        branches: List of branch objects with head_sha field.
        diff_stats: Callable(sha) -> (files_changed, lines_changed).
        file_paths: Callable(sha) -> list of file paths touched.
        config: Config object with max_tier2_commits, hot_paths, cold_paths.

    Returns:
        SelectedCommits with tier labels and importance scores.
    """
    max_tier2 = getattr(config, "max_tier2_commits", 1000)
    hot_paths = getattr(config, "hot_paths", []) or []
    cold_paths = getattr(config, "cold_paths", []) or []

    # Build lookup sets for Tier 1 classification
    tagged_shas = {t.target_sha for t in tags}
    branch_head_shas = {b.head_sha for b in branches}

    # Classify each commit
    tier1_shas: set[str] = set()
    commit_by_sha: dict[str, Any] = {}

    for c in commits:
        commit_by_sha[c.sha] = c

        # Root commit (no parents)
        if not c.parent_shas:
            tier1_shas.add(c.sha)

        # Merge commit
        if c.is_merge:
            tier1_shas.add(c.sha)

        # Tagged commit
        if c.sha in tagged_shas:
            tier1_shas.add(c.sha)

        # Branch head
        if c.sha in branch_head_shas:
            tier1_shas.add(c.sha)

        # Hot-path commit
        if hot_paths:
            touched = file_paths(c.sha)
            for fp in touched:
                if any(fnmatch.fnmatch(fp, pat) for pat in hot_paths):
                    tier1_shas.add(c.sha)
                    break

    # Score Tier 2 candidates
    tier2_candidates: list[tuple[str, float]] = []
    for c in commits:
        if c.sha in tier1_shas:
            continue
        files_changed, lines_changed = diff_stats(c.sha)
        touched = file_paths(c.sha)

        # Zero out contribution of cold-path files
        if cold_paths:
            non_cold_count = 0
            non_cold_lines = 0
            for fp in touched:
                is_cold = any(fnmatch.fnmatch(fp, pat) for pat in cold_paths)
                if not is_cold:
                    non_cold_count += 1
            # If all files are cold, score is 0
            if non_cold_count == 0 and touched:
                score = 0.0
            else:
                # Recompute with cold files zeroed
                score = float(files_changed) + (float(lines_changed) / 400.0)
                # If some files are cold, adjust files_changed to non-cold count
                if non_cold_count < len(touched) and touched:
                    score = float(non_cold_count) + (float(lines_changed) / 400.0)
        else:
            score = float(files_changed) + (float(lines_changed) / 400.0)

        tier2_candidates.append((c.sha, score))

    # Sort Tier 2 by score descending, then by sha for determinism
    tier2_candidates.sort(key=lambda x: (-x[1], x[0]))

    # Ensure most recent and earliest are always in Tier 2
    if tier2_candidates:
        # Find most recent and earliest by authored_at among tier2 candidates
        tier2_shas_set = {sha for sha, _ in tier2_candidates}
        tier2_commit_list = [c for c in commits if c.sha in tier2_shas_set]
        if tier2_commit_list:
            most_recent = max(tier2_commit_list, key=lambda c: c.authored_at)
            earliest = min(tier2_commit_list, key=lambda c: c.authored_at)
            # These must be in the selected set
            must_include = {most_recent.sha, earliest.sha}
        else:
            must_include = set()
    else:
        must_include = set()

    # Select Tier 2 within budget
    selected_tier2_shas: list[str] = []
    remaining_budget = max_tier2

    # First add must-include commits
    for sha, score in tier2_candidates:
        if sha in must_include:
            selected_tier2_shas.append(sha)
            remaining_budget -= 1

    # Then fill remaining budget from sorted list
    for sha, score in tier2_candidates:
        if remaining_budget <= 0:
            break
        if sha in must_include:
            continue  # already added
        selected_tier2_shas.append(sha)
        remaining_budget -= 1

    # Build score lookup
    score_by_sha = {sha: score for sha, score in tier2_candidates}

    # Build result
    result_commits: list[SelectedCommit] = []

    # Add Tier 1 commits
    for c in commits:
        if c.sha in tier1_shas:
            touched = file_paths(c.sha)
            result_commits.append(SelectedCommit(
                sha=c.sha,
                subject=c.subject,
                author_name=c.author_name,
                author_email=c.author_email,
                authored_at=c.authored_at,
                committer_name=c.committer_name,
                committer_email=c.committer_email,
                committed_at=c.committed_at,
                parent_shas=c.parent_shas,
                is_merge=c.is_merge,
                tier="structural",
                importance_score=-1.0,
                files_changed=touched,
            ))

    # Add Tier 2 commits (in score-descending order)
    tier2_selected_set = set(selected_tier2_shas)
    # Re-sort to maintain score-descending order
    tier2_ordered = [(sha, score_by_sha.get(sha, 0.0)) for sha in selected_tier2_shas]
    tier2_ordered.sort(key=lambda x: (-x[1], x[0]))

    for sha, score in tier2_ordered:
        c = commit_by_sha[sha]
        touched = file_paths(c.sha)
        result_commits.append(SelectedCommit(
            sha=c.sha,
            subject=c.subject,
            author_name=c.author_name,
            author_email=c.author_email,
            authored_at=c.authored_at,
            committer_name=c.committer_name,
            committer_email=c.committer_email,
            committed_at=c.committed_at,
            parent_shas=c.parent_shas,
            is_merge=c.is_merge,
            tier="scored",
            importance_score=score,
            files_changed=touched,
        ))

    return SelectedCommits(commits=result_commits)
