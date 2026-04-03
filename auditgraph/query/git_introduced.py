"""git_introduced: When was this file introduced.

Reads the reverse index and commit entities to find the earliest
commit that added the given file. Also checks for succeeded_from
lineage links to report file rename history.
"""

from __future__ import annotations

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


def _find_lineage(pkg_root: Path, file_eid: str) -> list[dict[str, Any]]:
    """Find succeeded_from links where from_id matches the given file entity.

    Returns list of dicts: [{old_path, confidence, detection_method}]
    """
    lineage: list[dict[str, Any]] = []
    links_dir = pkg_root / "links"
    if not links_dir.exists():
        return lineage
    for path in links_dir.rglob("lnk_*.json"):
        try:
            link = read_json(path)
        except Exception:
            continue
        if (link.get("type") == "succeeded_from"
                and link.get("from_id") == file_eid):
            evidence = link.get("evidence", [{}])
            ev = evidence[0] if evidence else {}
            lineage.append({
                "old_path": ev.get("old_path", ""),
                "confidence": link.get("confidence", 0.0),
                "detection_method": ev.get("detection_method", ""),
            })
    return lineage


def git_introduced(pkg_root: Path, file_path: str) -> dict[str, Any]:
    """Return the earliest commit that introduced the given file.

    Returns:
        {"status": "ok", "file": file_path, "commit": {...}, "lineage": [...]}
        or {"status": "error", "message": "..."}
    """
    file_eid = entity_id(f"file:{file_path}")
    index = _load_reverse_index(pkg_root)

    if file_eid not in index:
        return {"status": "error", "message": f"No provenance data for file: {file_path}"}

    commit_ids = index[file_eid]

    # Load all commit entities and find the earliest by authored_at
    commits: list[dict[str, Any]] = []
    for cid in commit_ids:
        try:
            entity = load_entity(pkg_root, cid)
        except (FileNotFoundError, KeyError):
            continue
        commits.append(entity)

    if not commits:
        return {"status": "error", "message": f"No commit entities found for file: {file_path}"}

    # Find earliest commit
    earliest = min(commits, key=lambda c: str(c.get("authored_at", "")))

    # Build tag map for this commit
    sha = str(earliest.get("sha", ""))
    tags = _get_tags_for_sha(pkg_root, sha)

    commit_dict: dict[str, Any] = {
        "sha": sha,
        "subject": str(earliest.get("subject", "")),
        "author_email": str(earliest.get("author_email", "")),
        "author_name": str(earliest.get("author_name", "")),
        "authored_at": str(earliest.get("authored_at", "")),
        "is_merge": bool(earliest.get("is_merge", False)),
        "parent_shas": list(earliest.get("parent_shas", [])),
        "tags": tags,
    }

    # Check for file lineage (succeeded_from links)
    lineage = _find_lineage(pkg_root, file_eid)

    return {
        "status": "ok",
        "file": file_path,
        "commit": commit_dict,
        "lineage": lineage,
    }


def _get_tags_for_sha(pkg_root: Path, sha: str) -> list[str]:
    """Find tag names pointing at the given commit sha."""
    tags: list[str] = []
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return tags
    for path in entities_dir.rglob("tag_*.json"):
        entity = read_json(path)
        if entity.get("type") == "tag" and str(entity.get("target_sha", "")) == sha:
            tags.append(str(entity.get("name", "")))
    return tags
