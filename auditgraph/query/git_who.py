"""git_who: Who changed this file.

Reads the reverse index and commit/author entities to aggregate
author information for a given file path.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from auditgraph.storage.artifacts import read_json
from auditgraph.storage.hashing import entity_id
from auditgraph.storage.loaders import load_entity


def _load_reverse_index(pkg_root: Path) -> dict[str, list[str]]:
    idx_path = pkg_root / "indexes" / "git-provenance" / "file-commits.json"
    if not idx_path.exists():
        return {}
    return read_json(idx_path)


def _load_commit_entity(pkg_root: Path, commit_id: str) -> dict[str, Any] | None:
    try:
        return load_entity(pkg_root, commit_id)
    except (FileNotFoundError, KeyError):
        return None


def _load_author_entity(pkg_root: Path, author_id: str) -> dict[str, Any] | None:
    try:
        return load_entity(pkg_root, author_id)
    except (FileNotFoundError, KeyError):
        return None


def git_who(pkg_root: Path, file_path: str) -> dict[str, Any]:
    """Return authors who modified the given file.

    Returns:
        {"status": "ok", "file": file_path, "authors": [...]}
        or {"status": "error", "message": "..."}
    """
    file_eid = entity_id(f"file:{file_path}")
    index = _load_reverse_index(pkg_root)

    if file_eid not in index:
        return {"status": "error", "message": f"No provenance data for file: {file_path}"}

    commit_ids = index[file_eid]

    # Load commit entities and group by author email
    commits_by_email: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cid in commit_ids:
        commit = _load_commit_entity(pkg_root, cid)
        if commit:
            email = str(commit.get("author_email", ""))
            commits_by_email[email].append(commit)

    # Build author summaries
    authors: list[dict[str, Any]] = []
    from auditgraph.storage.hashing import deterministic_author_id

    # Determine repo_path from any loaded commit entity
    repo_path = ""
    for email, email_commits in commits_by_email.items():
        # We need repo_path for author entity lookup. Derive from commit ID.
        # The commit entities are stored in the same pkg_root.
        # Load the author entity to get name_aliases.
        break

    # Infer repo_path from the repo entity — scan entities for a repo_ entity
    # Simpler: load author entity by trying to find it from link data
    # Even simpler: the author entity's ID is deterministic from repo_path + email.
    # We can find repo_path from the repository entity in the same pkg_root.
    repo_path = _find_repo_path(pkg_root)

    for email in sorted(commits_by_email.keys()):
        email_commits = commits_by_email[email]
        timestamps = [str(c.get("authored_at", "")) for c in email_commits]
        timestamps = [t for t in timestamps if t]

        # Load author entity for name aliases
        names: list[str] = []
        if repo_path:
            author_eid = deterministic_author_id(repo_path, email)
            author = _load_author_entity(pkg_root, author_eid)
            if author:
                names = list(author.get("name_aliases", []))

        if not names:
            # Fallback: collect names from commit entities
            seen_names: set[str] = set()
            for c in email_commits:
                name = str(c.get("author_name", ""))
                if name:
                    seen_names.add(name)
            names = sorted(seen_names)

        authors.append({
            "email": email,
            "names": names,
            "commit_count": len(email_commits),
            "earliest": min(timestamps) if timestamps else "",
            "latest": max(timestamps) if timestamps else "",
        })

    return {"status": "ok", "file": file_path, "authors": authors}


def _find_repo_path(pkg_root: Path) -> str:
    """Find the repository path from a repo entity in the pkg_root."""
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return ""
    for path in entities_dir.rglob("repo_*.json"):
        entity = read_json(path)
        if entity.get("type") == "repository":
            return str(entity.get("path", ""))
    return ""
