"""Materializer for Git provenance entities and links.

Converts selected commits, tags, and repository metadata into entity dicts
and link dicts following the existing AuditGraph schema conventions.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from auditgraph.storage.hashing import (
    deterministic_author_id,
    deterministic_commit_id,
    deterministic_ref_id,
    deterministic_repo_id,
    deterministic_tag_id,
    entity_id,
    sha256_text,
)


# ---------------------------------------------------------------------------
# Link ID helper (mirrors link/rules.py pattern)
# ---------------------------------------------------------------------------


def _link_id(rule_id: str, from_id: str, to_id: str) -> str:
    return f"lnk_{sha256_text(rule_id + ':' + from_id + ':' + to_id)}"


# ---------------------------------------------------------------------------
# Entity builders
# ---------------------------------------------------------------------------


def build_commit_nodes(selected_commits: list[Any], repo_path: str) -> list[dict[str, Any]]:
    """Build commit entity dicts from selected commits."""
    nodes: list[dict[str, Any]] = []
    for c in selected_commits:
        subject_first_line = c.subject.split("\n")[0] if c.subject else ""
        node: dict[str, Any] = {
            "id": deterministic_commit_id(repo_path, c.sha),
            "type": "commit",
            # `name` is the human-readable label used by BM25 indexing,
            # `auditgraph node`, `auditgraph list --sort name`, and the
            # node_view query. For commits we use the first line of the
            # commit message (its "subject"), matching git's own convention.
            # The `subject` field is preserved separately for backwards
            # compatibility with code that already references it.
            "name": subject_first_line,
            "sha": c.sha,
            "subject": subject_first_line,
            "author_name": c.author_name,
            "author_email": c.author_email,
            "authored_at": c.authored_at,
            "is_merge": c.is_merge,
            "parent_shas": c.parent_shas,
            "tier": c.tier,
            "importance_score": c.importance_score,
        }
        # Committer fields: null when same as author
        if (c.committer_name == c.author_name
                and c.committer_email == c.author_email
                and c.committed_at == c.authored_at):
            node["committer_name"] = None
            node["committer_email"] = None
            node["committed_at"] = None
        else:
            node["committer_name"] = c.committer_name
            node["committer_email"] = c.committer_email
            node["committed_at"] = c.committed_at
        nodes.append(node)
    return nodes


def build_author_nodes(selected_commits: list[Any], repo_path: str) -> list[dict[str, Any]]:
    """Build AuthorIdentity entity dicts, deduped by email with sorted name aliases."""
    names_by_email: dict[str, set[str]] = defaultdict(set)
    for c in selected_commits:
        names_by_email[c.author_email].add(c.author_name)

    nodes: list[dict[str, Any]] = []
    for email in sorted(names_by_email.keys()):
        aliases = sorted(names_by_email[email])
        # `name` is the human-readable display label. Prefer the first
        # non-empty alias (the author's chosen display name); fall back to
        # the email address when the alias is empty so the entity is still
        # identifiable in BM25 search and node views.
        display_name = next((a for a in aliases if a), email)
        nodes.append({
            "id": deterministic_author_id(repo_path, email),
            "type": "author_identity",
            "name": display_name,
            "email": email,
            "name_aliases": aliases,
        })
    return nodes


def build_tag_nodes(tags: list[Any], repo_path: str) -> list[dict[str, Any]]:
    """Build Tag entity dicts."""
    nodes: list[dict[str, Any]] = []
    for t in tags:
        nodes.append({
            "id": deterministic_tag_id(repo_path, t.name),
            "type": "tag",
            "name": t.name,
            "tag_type": t.tag_type,
            "target_sha": t.target_sha,
            "tagger_name": t.tagger_name,
            "tagger_email": t.tagger_email,
            "tagged_at": t.tagged_at,
        })
    return nodes


def build_repo_node(repo_path: str) -> dict[str, Any]:
    """Build Repository entity dict."""
    p = Path(repo_path)
    return {
        "id": deterministic_repo_id(repo_path),
        "type": "repository",
        "path": repo_path,
        "name": p.name,
    }


def build_ref_nodes(branches: list[Any], repo_path: str) -> list[dict[str, Any]]:
    """Build Ref entity dicts for each branch."""
    nodes: list[dict[str, Any]] = []
    for b in branches:
        nodes.append({
            "id": deterministic_ref_id(repo_path, b.name),
            "type": "ref",
            "name": b.name,
            "ref_type": "branch",
            "head_sha": b.head_sha,
        })
    return nodes


def build_file_nodes(
    selected_commits: list[Any],
    repo_path: str,
) -> list[dict[str, Any]]:
    """Build `file` entity dicts for every distinct path in any commit's
    files_changed list.

    Per Spec 025, this is the sole creator of `file` entities. The schema
    matches the existing `extract_code_symbols` output exactly (clarification
    Q1) so existing tests and downstream consumers of `source_path` continue
    to work without change. All paths are treated uniformly regardless of
    git object kind (regular file, symlink, submodule) per clarification Q2.

    The function deduplicates paths across commits (a path touched by 100
    commits becomes 1 entity, not 100) and returns the result sorted by
    entity ID for determinism — matching the convention used by the other
    `build_*_nodes` functions in this module.

    The entity ID is derived via `entity_id(f"file:{path}")` using the
    same hashing function that `build_links()` uses to compute `modifies`
    link `to_id` values, guaranteeing the link targets resolve to real
    entities on disk after the stage runs.
    """
    paths: set[str] = set()
    for c in selected_commits:
        for file_path in getattr(c, "files_changed", []):
            if file_path:
                paths.add(file_path)

    nodes: list[dict[str, Any]] = []
    for path in sorted(paths):
        canonical_key = f"file:{path}"
        nodes.append({
            "id": entity_id(canonical_key),
            "type": "file",
            "name": path.rsplit("/", 1)[-1],
            "canonical_key": canonical_key,
            "source_path": path,
        })

    nodes.sort(key=lambda n: n["id"])
    return nodes


# ---------------------------------------------------------------------------
# Link builders
# ---------------------------------------------------------------------------


def build_links(
    commit_nodes: list[dict[str, Any]],
    author_nodes: list[dict[str, Any]],
    tag_nodes: list[dict[str, Any]],
    repo_node: dict[str, Any],
    selected_commits: list[Any],
    repo_path: str,
    *,
    ref_nodes: list[dict[str, Any]] | None = None,
    branches: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Build all relationship link dicts.

    Link types: modifies, parent_of, authored_by, contains, tags, on_branch.
    """
    links: list[dict[str, Any]] = []

    # Build lookup maps
    commit_id_by_sha: dict[str, str] = {}
    for node in commit_nodes:
        commit_id_by_sha[node["sha"]] = node["id"]

    author_id_by_email: dict[str, str] = {}
    for node in author_nodes:
        author_id_by_email[node["email"]] = node["id"]

    tag_id_by_name: dict[str, str] = {}
    for node in tag_nodes:
        tag_id_by_name[node["name"]] = node["id"]

    repo_id = repo_node["id"]

    for c in selected_commits:
        commit_id = commit_id_by_sha.get(c.sha)
        if not commit_id:
            continue

        # modifies links: commit -> file entity
        for file_path in getattr(c, "files_changed", []):
            file_ent_id = entity_id(f"file:{file_path}")
            links.append({
                "id": _link_id("link.git_modifies.v1", commit_id, file_ent_id),
                "from_id": commit_id,
                "to_id": file_ent_id,
                "type": "modifies",
                "rule_id": "link.git_modifies.v1",
                "confidence": 1.0,
                "authority": "authoritative",
                "evidence": [{"commit_sha": c.sha, "source_path": file_path}],
            })

        # parent_of links: child commit -> parent commit
        for parent_sha in c.parent_shas:
            parent_id = commit_id_by_sha.get(parent_sha)
            if parent_id:
                links.append({
                    "id": _link_id("link.git_parent.v1", commit_id, parent_id),
                    "from_id": commit_id,
                    "to_id": parent_id,
                    "type": "parent_of",
                    "rule_id": "link.git_parent.v1",
                    "confidence": 1.0,
                    "authority": "authoritative",
                    "evidence": [{"child_sha": c.sha, "parent_sha": parent_sha}],
                })

        # authored_by links: commit -> author
        author_id = author_id_by_email.get(c.author_email)
        if author_id:
            links.append({
                "id": _link_id("link.git_authored_by.v1", commit_id, author_id),
                "from_id": commit_id,
                "to_id": author_id,
                "type": "authored_by",
                "rule_id": "link.git_authored_by.v1",
                "confidence": 1.0,
                "authority": "authoritative",
                "evidence": [{"commit_sha": c.sha, "author_email": c.author_email}],
            })

        # contains links: repo -> commit
        links.append({
            "id": _link_id("link.git_contains.v1", repo_id, commit_id),
            "from_id": repo_id,
            "to_id": commit_id,
            "type": "contains",
            "rule_id": "link.git_contains.v1",
            "confidence": 1.0,
            "authority": "authoritative",
        })

    # tags links: tag -> commit
    for tag_node in tag_nodes:
        target_sha = tag_node["target_sha"]
        target_commit_id = commit_id_by_sha.get(target_sha)
        if target_commit_id:
            tag_id = tag_node["id"]
            links.append({
                "id": _link_id("link.git_tags.v1", tag_id, target_commit_id),
                "from_id": tag_id,
                "to_id": target_commit_id,
                "type": "tags",
                "rule_id": "link.git_tags.v1",
                "confidence": 1.0,
                "authority": "authoritative",
            })

    # on_branch links: HEAD commit -> ref node
    if ref_nodes and branches:
        ref_id_by_name: dict[str, str] = {}
        for rn in ref_nodes:
            ref_id_by_name[rn["name"]] = rn["id"]

        for b in branches:
            head_commit_id = commit_id_by_sha.get(b.head_sha)
            ref_id = ref_id_by_name.get(b.name)
            if head_commit_id and ref_id:
                links.append({
                    "id": _link_id("link.git_branch.v1", head_commit_id, ref_id),
                    "from_id": head_commit_id,
                    "to_id": ref_id,
                    "type": "on_branch",
                    "rule_id": "link.git_branch.v1",
                    "confidence": 1.0,
                    "authority": "authoritative",
                })

    return links


# ---------------------------------------------------------------------------
# Lineage links
# ---------------------------------------------------------------------------


def build_lineage_links(renames: list[Any], repo_path: str) -> list[dict[str, Any]]:
    """Build succeeded_from links from detected rename pairs.

    Each rename pair produces a link from the new file entity to the old file entity.
    The link carries confidence metadata based on detection method.

    Args:
        renames: List of RenamePair-like objects with old_path, new_path,
                 detection_method, confidence, and commit_sha.
        repo_path: Repository path (unused in link construction but kept for API consistency).

    Returns:
        List of succeeded_from link dicts.
    """
    links: list[dict[str, Any]] = []
    for r in renames:
        new_eid = entity_id(f"file:{r.new_path}")
        old_eid = entity_id(f"file:{r.old_path}")
        links.append({
            "id": _link_id("link.git_lineage.v1", new_eid, old_eid),
            "from_id": new_eid,
            "to_id": old_eid,
            "type": "succeeded_from",
            "rule_id": "link.git_lineage.v1",
            "confidence": r.confidence,
            "authority": "heuristic",
            "evidence": [{
                "commit_sha": r.commit_sha,
                "old_path": r.old_path,
                "new_path": r.new_path,
                "detection_method": r.detection_method,
            }],
        })
    return links


# ---------------------------------------------------------------------------
# Reverse index
# ---------------------------------------------------------------------------


def build_reverse_index(modifies_links: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build file_entity_id -> [commit_ids] reverse index from modifies links."""
    index: dict[str, list[str]] = defaultdict(list)
    for lnk in modifies_links:
        file_id = lnk["to_id"]
        commit_id = lnk["from_id"]
        if commit_id not in index[file_id]:
            index[file_id].append(commit_id)
    return dict(index)
