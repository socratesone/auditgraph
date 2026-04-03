"""git_log: What commits touched this file.

Reads the reverse index and commit/tag entities to return commits
ordered by authored_at descending.
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


def _load_tag_index(pkg_root: Path) -> dict[str, list[str]]:
    """Build sha -> [tag_names] mapping from tag entities."""
    tag_map: dict[str, list[str]] = {}
    entities_dir = pkg_root / "entities"
    if not entities_dir.exists():
        return tag_map
    for path in entities_dir.rglob("tag_*.json"):
        entity = read_json(path)
        if entity.get("type") == "tag":
            target_sha = str(entity.get("target_sha", ""))
            tag_name = str(entity.get("name", ""))
            if target_sha and tag_name:
                tag_map.setdefault(target_sha, []).append(tag_name)
    return tag_map


def git_log(pkg_root: Path, file_path: str) -> dict[str, Any]:
    """Return commits that modified the given file, ordered by authored_at descending.

    Returns:
        {"status": "ok", "file": file_path, "commits": [...]}
        or {"status": "error", "message": "..."}
    """
    file_eid = entity_id(f"file:{file_path}")
    index = _load_reverse_index(pkg_root)

    if file_eid not in index:
        return {"status": "error", "message": f"No provenance data for file: {file_path}"}

    commit_ids = index[file_eid]
    tag_map = _load_tag_index(pkg_root)

    commits: list[dict[str, Any]] = []
    for cid in commit_ids:
        try:
            entity = load_entity(pkg_root, cid)
        except (FileNotFoundError, KeyError):
            continue

        sha = str(entity.get("sha", ""))
        commits.append({
            "sha": sha,
            "subject": str(entity.get("subject", "")),
            "author_email": str(entity.get("author_email", "")),
            "author_name": str(entity.get("author_name", "")),
            "authored_at": str(entity.get("authored_at", "")),
            "is_merge": bool(entity.get("is_merge", False)),
            "parent_shas": list(entity.get("parent_shas", [])),
            "tags": tag_map.get(sha, []),
        })

    # Sort by authored_at descending
    commits.sort(key=lambda c: c["authored_at"], reverse=True)

    return {"status": "ok", "file": file_path, "commits": commits}
