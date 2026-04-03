"""Dulwich adapter for reading Git repository metadata.

Provides a read-only interface to walk commits, compute diff stats,
enumerate tags, and list branches from a local Git repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from dulwich.diff_tree import (
    CHANGE_ADD,
    CHANGE_DELETE,
    CHANGE_RENAME,
    RenameDetector,
    tree_changes,
)
from dulwich.objects import Commit, Tag, Tree
from dulwich.repo import Repo

# Hardcoded similarity threshold for rename detection (v1 -- not configurable)
_RENAME_SIMILARITY_THRESHOLD = 70


# ---------------------------------------------------------------------------
# Data classes for reader output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenamePair:
    """A detected file rename/move within a single commit."""
    old_path: str
    new_path: str
    detection_method: str  # "rename", "similarity", "basename_match"
    confidence: float
    commit_sha: str


@dataclass(frozen=True)
class CommitInfo:
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


@dataclass(frozen=True)
class TagInfo:
    name: str
    tag_type: str  # "lightweight" or "annotated"
    target_sha: str
    tagger_name: str | None
    tagger_email: str | None
    tagged_at: str | None


@dataclass(frozen=True)
class BranchInfo:
    name: str
    head_sha: str


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _decode_bytes(raw: bytes, encoding_hint: bytes | None = None) -> str:
    """Decode raw bytes with fallback chain: declared encoding -> utf-8 -> latin-1."""
    if encoding_hint:
        hint = encoding_hint.decode("ascii", errors="ignore").strip().lower()
        for enc in (hint, "utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")  # latin-1 never fails


def _parse_author(raw_author: bytes, encoding_hint: bytes | None = None) -> tuple[str, str]:
    """Parse 'Name <email>' into (name, email)."""
    decoded = _decode_bytes(raw_author, encoding_hint)
    if "<" in decoded and ">" in decoded:
        name = decoded.split("<")[0].strip()
        email = decoded.split("<")[1].rstrip(">").strip()
        return name, email
    return decoded, ""


def _timestamp_to_iso(timestamp: int, tz_offset: int = 0) -> str:
    """Convert Unix timestamp + offset to ISO-8601 string."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _subject_from_message(raw_message: bytes, encoding_hint: bytes | None = None) -> str:
    """Extract first line of commit message as subject."""
    decoded = _decode_bytes(raw_message, encoding_hint)
    first_line = decoded.split("\n")[0].strip()
    return first_line


def _count_blob_lines(store, blob_id: bytes) -> int:
    """Count lines in a blob object."""
    try:
        blob = store[blob_id]
        return blob.data.count(b"\n")
    except Exception:
        return 0


def _flatten_tree(store, tree_id: bytes, prefix: str = "") -> dict[str, bytes]:
    """Flatten a tree into {path: blob_sha} mapping (recursive)."""
    result: dict[str, bytes] = {}
    try:
        tree = store[tree_id]
    except Exception:
        return result
    if not isinstance(tree, Tree):
        return result
    for item in tree.items():
        path = f"{prefix}{item.path.decode('utf-8', errors='replace')}"
        obj = store[item.sha]
        if isinstance(obj, Tree):
            result.update(_flatten_tree(store, item.sha, path + "/"))
        else:
            result[path] = item.sha
    return result


# ---------------------------------------------------------------------------
# GitReader
# ---------------------------------------------------------------------------


class GitReader:
    """Read-only adapter for a local Git repository via dulwich."""

    def __init__(self, repo_path: Path | str) -> None:
        path = Path(repo_path)
        if not (path / ".git").is_dir():
            raise FileNotFoundError(f"No .git directory found at {path}")
        self._repo = Repo(str(path))
        self._path = path

    def walk_commits(self) -> list[CommitInfo]:
        """Walk all reachable commits from HEAD, returning CommitInfo list."""
        try:
            head_sha = self._repo.head()
        except KeyError:
            # Empty repo -- no HEAD
            return []

        commits: list[CommitInfo] = []
        for entry in self._repo.get_walker():
            c = entry.commit
            encoding_hint = getattr(c, "encoding", None)
            author_name, author_email = _parse_author(c.author, encoding_hint)
            committer_name, committer_email = _parse_author(c.committer, encoding_hint)
            authored_at = _timestamp_to_iso(c.author_time, c.author_timezone)
            committed_at = _timestamp_to_iso(c.commit_time, c.commit_timezone)
            subject = _subject_from_message(c.message, encoding_hint)
            parent_shas = [p.decode("ascii") for p in c.parents]
            is_merge = len(c.parents) > 1

            commits.append(CommitInfo(
                sha=c.id.decode("ascii"),
                subject=subject,
                author_name=author_name,
                author_email=author_email,
                authored_at=authored_at,
                committer_name=committer_name,
                committer_email=committer_email,
                committed_at=committed_at,
                parent_shas=parent_shas,
                is_merge=is_merge,
            ))
        return commits

    def diff_stat(self, commit_sha: str) -> tuple[int, int]:
        """Compute (files_changed, lines_changed) for a commit.

        For root commits (no parents), compares against an empty tree.
        lines_changed counts total added + removed lines.
        """
        commit = self._repo[commit_sha.encode("ascii")]
        if not isinstance(commit, Commit):
            return (0, 0)

        store = self._repo.object_store

        if commit.parents:
            parent = self._repo[commit.parents[0]]
            old_tree_id = parent.tree
        else:
            # Root commit: compare against empty tree
            empty_tree = Tree()
            store.add_object(empty_tree)
            old_tree_id = empty_tree.id

        new_tree_id = commit.tree

        # Flatten both trees to get file-level diff
        old_files = _flatten_tree(store, old_tree_id)
        new_files = _flatten_tree(store, new_tree_id)

        all_paths = set(old_files.keys()) | set(new_files.keys())
        files_changed = 0
        lines_changed = 0

        for path in all_paths:
            old_sha = old_files.get(path)
            new_sha = new_files.get(path)
            if old_sha == new_sha:
                continue
            files_changed += 1
            old_lines = _count_blob_lines(store, old_sha) if old_sha else 0
            new_lines = _count_blob_lines(store, new_sha) if new_sha else 0
            lines_changed += abs(new_lines - old_lines)

        return (files_changed, lines_changed)

    def diff_files(self, commit_sha: str) -> list[str]:
        """Return list of file paths changed by a commit."""
        commit = self._repo[commit_sha.encode("ascii")]
        if not isinstance(commit, Commit):
            return []

        store = self._repo.object_store

        if commit.parents:
            parent = self._repo[commit.parents[0]]
            old_tree_id = parent.tree
        else:
            empty_tree = Tree()
            store.add_object(empty_tree)
            old_tree_id = empty_tree.id

        old_files = _flatten_tree(store, old_tree_id)
        new_files = _flatten_tree(store, commit.tree)

        changed: list[str] = []
        for path in sorted(set(old_files.keys()) | set(new_files.keys())):
            if old_files.get(path) != new_files.get(path):
                changed.append(path)
        return changed

    def list_tags(self) -> list[TagInfo]:
        """Enumerate all tags in the repository."""
        tags: list[TagInfo] = []
        for ref_name in sorted(self._repo.refs.keys()):
            if not ref_name.startswith(b"refs/tags/"):
                continue
            tag_name = ref_name[len(b"refs/tags/"):].decode("utf-8", errors="replace")
            obj_sha = self._repo.refs[ref_name]
            obj = self._repo[obj_sha]

            if isinstance(obj, Tag):
                # Annotated tag
                tagger_name, tagger_email = _parse_author(obj.tagger) if obj.tagger else ("", "")
                tagged_at = _timestamp_to_iso(obj.tag_time) if hasattr(obj, "tag_time") and obj.tag_time else None
                # Resolve target: the tag object points to a commit
                target_sha = obj._object_sha.decode("ascii") if hasattr(obj, "_object_sha") else obj_sha.decode("ascii")
                tags.append(TagInfo(
                    name=tag_name,
                    tag_type="annotated",
                    target_sha=target_sha,
                    tagger_name=tagger_name or None,
                    tagger_email=tagger_email or None,
                    tagged_at=tagged_at,
                ))
            elif isinstance(obj, Commit):
                # Lightweight tag
                tags.append(TagInfo(
                    name=tag_name,
                    tag_type="lightweight",
                    target_sha=obj.id.decode("ascii"),
                    tagger_name=None,
                    tagger_email=None,
                    tagged_at=None,
                ))
        return tags

    def list_branches(self) -> list[BranchInfo]:
        """Enumerate all local branches."""
        branches: list[BranchInfo] = []
        try:
            head_sha = self._repo.head()
        except KeyError:
            # Empty repo
            return []

        for ref_name in sorted(self._repo.refs.keys()):
            if not ref_name.startswith(b"refs/heads/"):
                continue
            branch_name = ref_name[len(b"refs/heads/"):].decode("utf-8", errors="replace")
            sha = self._repo.refs[ref_name].decode("ascii")
            branches.append(BranchInfo(name=branch_name, head_sha=sha))
        return branches

    def detect_renames(self, commit_sha: str) -> list[RenamePair]:
        """Detect file renames/moves in a single commit.

        Uses dulwich RenameDetector with 70% similarity threshold, then
        falls back to basename-match heuristic for remaining add+delete pairs.

        Returns list of RenamePair with detection_method and confidence:
          - "rename" (exact, same blob sha): confidence 1.0
          - "similarity" (>70% content match, different blob sha): confidence 0.8
          - "basename_match" (same basename, different dir, not caught by dulwich): confidence 0.6
        """
        commit = self._repo[commit_sha.encode("ascii")]
        if not isinstance(commit, Commit):
            return []

        store = self._repo.object_store

        if commit.parents:
            parent = self._repo[commit.parents[0]]
            old_tree_id = parent.tree
        else:
            empty_tree = Tree()
            store.add_object(empty_tree)
            old_tree_id = empty_tree.id

        new_tree_id = commit.tree

        # Phase 1: Use dulwich RenameDetector to find renames (exact + similarity)
        detector = RenameDetector(store, rename_threshold=_RENAME_SIMILARITY_THRESHOLD)
        changes = list(tree_changes(store, old_tree_id, new_tree_id, rename_detector=detector))

        results: list[RenamePair] = []
        consumed_adds: set[str] = set()
        consumed_deletes: set[str] = set()

        for change in changes:
            if change.type == CHANGE_RENAME:
                old_path = change.old.path.decode("utf-8", errors="replace")
                new_path = change.new.path.decode("utf-8", errors="replace")
                consumed_adds.add(new_path)
                consumed_deletes.add(old_path)

                # Distinguish exact rename (same blob sha) from similarity rename
                if change.old.sha == change.new.sha:
                    results.append(RenamePair(
                        old_path=old_path,
                        new_path=new_path,
                        detection_method="rename",
                        confidence=1.0,
                        commit_sha=commit_sha,
                    ))
                else:
                    results.append(RenamePair(
                        old_path=old_path,
                        new_path=new_path,
                        detection_method="similarity",
                        confidence=0.8,
                        commit_sha=commit_sha,
                    ))

        # Phase 2 (T043): Basename-match heuristic for remaining add+delete pairs
        adds: dict[str, str] = {}  # basename -> full path
        deletes: dict[str, str] = {}  # basename -> full path

        for change in changes:
            if change.type == CHANGE_ADD:
                path = change.new.path.decode("utf-8", errors="replace")
                if path not in consumed_adds:
                    basename = path.rsplit("/", 1)[-1] if "/" in path else path
                    adds[basename] = path
            elif change.type == CHANGE_DELETE:
                path = change.old.path.decode("utf-8", errors="replace")
                if path not in consumed_deletes:
                    basename = path.rsplit("/", 1)[-1] if "/" in path else path
                    deletes[basename] = path

        # Match adds and deletes with same basename but different directory
        for basename in sorted(adds.keys()):
            if basename in deletes:
                add_path = adds[basename]
                del_path = deletes[basename]
                # Must be in different directories to qualify as basename match
                add_dir = add_path.rsplit("/", 1)[0] if "/" in add_path else ""
                del_dir = del_path.rsplit("/", 1)[0] if "/" in del_path else ""
                if add_dir != del_dir:
                    results.append(RenamePair(
                        old_path=del_path,
                        new_path=add_path,
                        detection_method="basename_match",
                        confidence=0.6,
                        commit_sha=commit_sha,
                    ))

        return results

    def close(self) -> None:
        self._repo.close()
