"""Deterministic Git fixture repository generators using dulwich.

Each function takes a `tmp_path` (pathlib.Path) and returns the repo path.
All fixtures are deterministic: same content produces same Git object hashes.

Usage:
    repo_path = linear_repo(tmp_path / "linear")
"""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path
from typing import Optional

from dulwich.objects import Blob, Commit, Tag, Tree
from dulwich.repo import Repo


# Fixed timestamps for determinism (seconds since epoch + timezone offset)
_FIXED_AUTHOR_TIME = 1700000000  # 2023-11-14T22:13:20Z
_FIXED_TIMEZONE = 0  # UTC

# Fixed author identities
AUTHOR_ALICE = (b"Alice Developer", b"alice@example.com")
AUTHOR_BOB = (b"Bob Reviewer", b"bob@example.com")
AUTHOR_ALICE_ALT = (b"Alice D.", b"alice@example.com")  # Same email, different name


def _make_blob(repo: Repo, content: bytes) -> Blob:
    """Create and store a blob object."""
    blob = Blob.from_string(content)
    repo.object_store.add_object(blob)
    return blob


def _make_tree(repo: Repo, entries: dict[bytes, tuple[int, bytes]]) -> Tree:
    """Create and store a tree object.

    entries: {name: (mode, sha)}
    """
    tree = Tree()
    for name, (mode, sha) in sorted(entries.items()):
        tree.add(name, mode, sha)
    repo.object_store.add_object(tree)
    return tree


def _make_nested_tree(repo: Repo, file_map: dict[str, bytes]) -> Tree:
    """Create a tree from a flat path->content mapping, supporting nested directories.

    file_map: {"path/to/file.py": b"content"}
    """
    # Group files by top-level directory vs root files
    dirs: dict[str, dict[str, bytes]] = {}
    root_files: dict[str, bytes] = {}

    for path, content in file_map.items():
        parts = path.split("/", 1)
        if len(parts) == 1:
            root_files[path] = content
        else:
            dirname, rest = parts
            if dirname not in dirs:
                dirs[dirname] = {}
            dirs[dirname][rest] = content

    entries: dict[bytes, tuple[int, bytes]] = {}

    # Add root files
    for name, content in root_files.items():
        blob = _make_blob(repo, content)
        entries[name.encode()] = (stat.S_IFREG | 0o644, blob.id)

    # Add subdirectories (recursive)
    for dirname, subfiles in dirs.items():
        subtree = _make_nested_tree(repo, subfiles)
        entries[dirname.encode()] = (stat.S_IFDIR, subtree.id)

    return _make_tree(repo, entries)


def _make_commit(
    repo: Repo,
    tree: Tree,
    message: bytes,
    author: tuple[bytes, bytes],
    committer: tuple[bytes, bytes] | None = None,
    parents: list[bytes] | None = None,
    timestamp: int | None = None,
    commit_offset: int = 0,
) -> Commit:
    """Create and store a commit object.

    commit_offset: added to _FIXED_AUTHOR_TIME to create distinct timestamps per commit.
    """
    if committer is None:
        committer = author
    if parents is None:
        parents = []
    if timestamp is None:
        timestamp = _FIXED_AUTHOR_TIME + commit_offset

    commit = Commit()
    commit.tree = tree.id
    commit.author = author[0] + b" <" + author[1] + b">"
    commit.committer = committer[0] + b" <" + committer[1] + b">"
    commit.author_time = timestamp
    commit.author_timezone = _FIXED_TIMEZONE
    commit.commit_time = timestamp
    commit.commit_timezone = _FIXED_TIMEZONE
    commit.encoding = b"UTF-8"
    commit.message = message
    commit.parents = parents
    repo.object_store.add_object(commit)
    return commit


def linear_repo(tmp_path: Path) -> Path:
    """Create a repo with 5 linear commits, 3 files, 2 authors (one email with 2 name variants).

    Commit history (oldest first):
      1. Alice: add README.md
      2. Bob: add src/main.py
      3. Alice (alt name): add src/utils.py
      4. Bob: modify src/main.py
      5. Alice: modify README.md
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    # Commit 1: Alice adds README.md
    tree1 = _make_nested_tree(repo, {"README.md": b"# Project\nInitial readme.\n"})
    c1 = _make_commit(repo, tree1, b"Add README.md\n", AUTHOR_ALICE, commit_offset=0)

    # Commit 2: Bob adds src/main.py
    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Project\nInitial readme.\n",
        "src/main.py": b"def main():\n    pass\n",
    })
    c2 = _make_commit(repo, tree2, b"Add main.py\n", AUTHOR_BOB, parents=[c1.id], commit_offset=100)

    # Commit 3: Alice (alt name) adds src/utils.py
    tree3 = _make_nested_tree(repo, {
        "README.md": b"# Project\nInitial readme.\n",
        "src/main.py": b"def main():\n    pass\n",
        "src/utils.py": b"def helper():\n    return True\n",
    })
    c3 = _make_commit(repo, tree3, b"Add utils.py\n", AUTHOR_ALICE_ALT, parents=[c2.id], commit_offset=200)

    # Commit 4: Bob modifies src/main.py
    tree4 = _make_nested_tree(repo, {
        "README.md": b"# Project\nInitial readme.\n",
        "src/main.py": b"from utils import helper\n\ndef main():\n    helper()\n",
        "src/utils.py": b"def helper():\n    return True\n",
    })
    c4 = _make_commit(repo, tree4, b"Use helper in main\n", AUTHOR_BOB, parents=[c3.id], commit_offset=300)

    # Commit 5: Alice modifies README.md
    tree5 = _make_nested_tree(repo, {
        "README.md": b"# Project\nUpdated readme with usage.\n",
        "src/main.py": b"from utils import helper\n\ndef main():\n    helper()\n",
        "src/utils.py": b"def helper():\n    return True\n",
    })
    c5 = _make_commit(repo, tree5, b"Update README\n", AUTHOR_ALICE, parents=[c4.id], commit_offset=400)

    # Set HEAD to main branch pointing at c5
    repo.refs[b"refs/heads/main"] = c5.id
    repo.refs[b"HEAD"] = c5.id
    repo.close()
    return repo_path


def merge_repo(tmp_path: Path) -> Path:
    """Create a repo with a branch and merge commit, 2 branches.

    Topology:
      c1 -- c2 -- c4 (merge)  [main]
              \\       /
               c3         [feature]
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    # c1: initial
    tree1 = _make_nested_tree(repo, {"README.md": b"# Merge Test\n"})
    c1 = _make_commit(repo, tree1, b"Initial commit\n", AUTHOR_ALICE, commit_offset=0)

    # c2: main branch continues
    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Merge Test\n",
        "main_file.py": b"# main branch work\n",
    })
    c2 = _make_commit(repo, tree2, b"Main branch work\n", AUTHOR_ALICE, parents=[c1.id], commit_offset=100)

    # c3: feature branch from c1
    tree3 = _make_nested_tree(repo, {
        "README.md": b"# Merge Test\n",
        "feature.py": b"# feature branch work\n",
    })
    c3 = _make_commit(repo, tree3, b"Feature branch work\n", AUTHOR_BOB, parents=[c1.id], commit_offset=150)

    # c4: merge commit (both parents)
    tree4 = _make_nested_tree(repo, {
        "README.md": b"# Merge Test\n",
        "main_file.py": b"# main branch work\n",
        "feature.py": b"# feature branch work\n",
    })
    c4 = _make_commit(repo, tree4, b"Merge feature into main\n", AUTHOR_ALICE, parents=[c2.id, c3.id], commit_offset=200)

    repo.refs[b"refs/heads/main"] = c4.id
    repo.refs[b"refs/heads/feature"] = c3.id
    repo.refs[b"HEAD"] = c4.id
    repo.close()
    return repo_path


def rename_repo(tmp_path: Path) -> Path:
    """Create a repo with a file rename (simulating git mv).

    Commits:
      1. Add old_name.py
      2. Rename old_name.py -> new_name.py (delete old, add new with same content)
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    # c1: add original file
    tree1 = _make_nested_tree(repo, {
        "README.md": b"# Rename Test\n",
        "old_name.py": b"def foo():\n    return 42\n",
    })
    c1 = _make_commit(repo, tree1, b"Add old_name.py\n", AUTHOR_ALICE, commit_offset=0)

    # c2: rename old_name.py -> new_name.py (same content = exact rename)
    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Rename Test\n",
        "new_name.py": b"def foo():\n    return 42\n",
    })
    c2 = _make_commit(repo, tree2, b"Rename old_name.py to new_name.py\n", AUTHOR_ALICE, parents=[c1.id], commit_offset=100)

    repo.refs[b"refs/heads/main"] = c2.id
    repo.refs[b"HEAD"] = c2.id
    repo.close()
    return repo_path


def tag_repo(tmp_path: Path) -> Path:
    """Create a repo with 1 lightweight tag and 1 annotated tag.

    Commits:
      1. Initial commit -> lightweight tag "v0.1.0"
      2. Second commit -> annotated tag "v1.0.0"
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    # c1: initial
    tree1 = _make_nested_tree(repo, {"README.md": b"# Tag Test\nVersion 0.1\n"})
    c1 = _make_commit(repo, tree1, b"Initial release\n", AUTHOR_ALICE, commit_offset=0)

    # Lightweight tag at c1
    repo.refs[b"refs/tags/v0.1.0"] = c1.id

    # c2: second commit
    tree2 = _make_nested_tree(repo, {"README.md": b"# Tag Test\nVersion 1.0\n"})
    c2 = _make_commit(repo, tree2, b"Release v1.0.0\n", AUTHOR_BOB, parents=[c1.id], commit_offset=100)

    # Annotated tag at c2
    tag_obj = Tag()
    tag_obj.name = b"v1.0.0"
    tag_obj.message = b"Release version 1.0.0\n"
    tag_obj.tagger = AUTHOR_BOB[0] + b" <" + AUTHOR_BOB[1] + b">"
    tag_obj.tag_time = _FIXED_AUTHOR_TIME + 100
    tag_obj.tag_timezone = _FIXED_TIMEZONE
    tag_obj._object_class = Commit
    tag_obj._object_sha = c2.id
    repo.object_store.add_object(tag_obj)
    repo.refs[b"refs/tags/v1.0.0"] = tag_obj.id

    repo.refs[b"refs/heads/main"] = c2.id
    repo.refs[b"HEAD"] = c2.id
    repo.close()
    return repo_path


def large_repo(tmp_path: Path, num_commits: int = 50) -> Path:
    """Create a repo with N commits for budget/performance testing.

    Each commit modifies a single file with incrementing content to ensure unique trees.
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    parent_ids: list[bytes] = []

    for i in range(num_commits):
        content = f"# File content at commit {i}\nline_count = {i}\n".encode()
        tree = _make_nested_tree(repo, {
            "README.md": b"# Large Repo Test\n",
            "data.py": content,
        })
        author = AUTHOR_ALICE if i % 2 == 0 else AUTHOR_BOB
        commit = _make_commit(
            repo,
            tree,
            f"Commit number {i}\n".encode(),
            author,
            parents=parent_ids,
            commit_offset=i * 60,
        )
        parent_ids = [commit.id]

    repo.refs[b"refs/heads/main"] = parent_ids[0]
    repo.refs[b"HEAD"] = parent_ids[0]
    repo.close()
    return repo_path


def encoding_repo(tmp_path: Path) -> Path:
    """Create a repo with a commit from a non-UTF-8 author name.

    Uses latin-1 encoding for the author name containing accented characters.
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    tree1 = _make_nested_tree(repo, {"README.md": b"# Encoding Test\n"})

    # Create commit with non-UTF-8 author name
    # Dulwich stores raw bytes, so we can use latin-1 encoded bytes directly
    non_utf8_author = ("Ren\xe9 M\xfcller".encode("latin-1"), b"rene@example.com")

    commit = Commit()
    commit.tree = tree1.id
    commit.author = non_utf8_author[0] + b" <" + non_utf8_author[1] + b">"
    commit.committer = non_utf8_author[0] + b" <" + non_utf8_author[1] + b">"
    commit.author_time = _FIXED_AUTHOR_TIME
    commit.author_timezone = _FIXED_TIMEZONE
    commit.commit_time = _FIXED_AUTHOR_TIME
    commit.commit_timezone = _FIXED_TIMEZONE
    commit.encoding = b"ISO-8859-1"
    commit.message = b"Commit with non-UTF-8 author\n"
    commit.parents = []
    repo.object_store.add_object(commit)

    repo.refs[b"refs/heads/main"] = commit.id
    repo.refs[b"HEAD"] = commit.id
    repo.close()
    return repo_path


def hot_cold_repo(tmp_path: Path) -> Path:
    """Create a repo with commits touching both hot-path and cold-path files.

    Files:
      - src/core.py (hot path candidate)
      - package-lock.json (cold path: matches *.lock pattern)
      - build/output.generated.js (cold path: matches *.generated.*)
      - src/config.py (normal file)

    Commits:
      1. Add all files
      2. Modify src/core.py only (hot path commit)
      3. Modify package-lock.json only (cold path commit)
      4. Modify build/output.generated.js only (cold path commit)
      5. Modify src/config.py and src/core.py (mixed commit)
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    base_files = {
        "src/core.py": b"# core module\ndef init():\n    pass\n",
        "package-lock.json": b'{"lockfileVersion": 1}\n',
        "build/output.generated.js": b"// generated\nvar x = 1;\n",
        "src/config.py": b"# config\nDEBUG = False\n",
    }

    # c1: add all files
    tree1 = _make_nested_tree(repo, base_files)
    c1 = _make_commit(repo, tree1, b"Add initial files\n", AUTHOR_ALICE, commit_offset=0)

    # c2: modify hot path only
    files2 = {**base_files, "src/core.py": b"# core module v2\ndef init():\n    setup()\n"}
    tree2 = _make_nested_tree(repo, files2)
    c2 = _make_commit(repo, tree2, b"Update core module\n", AUTHOR_BOB, parents=[c1.id], commit_offset=100)

    # c3: modify cold path only
    files3 = {**files2, "package-lock.json": b'{"lockfileVersion": 2}\n'}
    tree3 = _make_nested_tree(repo, files3)
    c3 = _make_commit(repo, tree3, b"Update lock file\n", AUTHOR_ALICE, parents=[c2.id], commit_offset=200)

    # c4: modify cold path only
    files4 = {**files3, "build/output.generated.js": b"// generated v2\nvar x = 2;\n"}
    tree4 = _make_nested_tree(repo, files4)
    c4 = _make_commit(repo, tree4, b"Regenerate output\n", AUTHOR_BOB, parents=[c3.id], commit_offset=300)

    # c5: mixed (hot + normal)
    files5 = {
        **files4,
        "src/core.py": b"# core module v3\ndef init():\n    setup()\n    validate()\n",
        "src/config.py": b"# config\nDEBUG = True\n",
    }
    tree5 = _make_nested_tree(repo, files5)
    c5 = _make_commit(repo, tree5, b"Update core and config\n", AUTHOR_ALICE, parents=[c4.id], commit_offset=400)

    repo.refs[b"refs/heads/main"] = c5.id
    repo.refs[b"HEAD"] = c5.id
    repo.close()
    return repo_path


def similarity_rename_repo(tmp_path: Path) -> Path:
    """Create a repo with a similarity-based rename (>70% content match, different filename).

    Commits:
      1. Add utils.py with content
      2. Delete utils.py, add helpers.py with similar content
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    original_content = b"def helper_one():\n    return 1\ndef helper_two():\n    return 2\ndef helper_three():\n    return 3\ndef helper_four():\n    return 4\ndef helper_five():\n    return 5\n"
    # ~80% similar: changed last function
    similar_content = b"def helper_one():\n    return 1\ndef helper_two():\n    return 2\ndef helper_three():\n    return 3\ndef helper_four():\n    return 4\ndef helper_six():\n    return 6\n"

    tree1 = _make_nested_tree(repo, {
        "README.md": b"# Similarity Test\n",
        "utils.py": original_content,
    })
    c1 = _make_commit(repo, tree1, b"Add utils.py\n", AUTHOR_ALICE, commit_offset=0)

    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Similarity Test\n",
        "helpers.py": similar_content,
    })
    c2 = _make_commit(repo, tree2, b"Rename utils.py to helpers.py with changes\n", AUTHOR_ALICE, parents=[c1.id], commit_offset=100)

    repo.refs[b"refs/heads/main"] = c2.id
    repo.refs[b"HEAD"] = c2.id
    repo.close()
    return repo_path


def basename_match_repo(tmp_path: Path) -> Path:
    """Create a repo where a file moves between directories with very different content.

    The content similarity is below 70% so dulwich rename detector won't catch it,
    but the basename is the same -- triggering the basename_match heuristic at 0.6 confidence.

    Commits:
      1. Add src/config.py with original content
      2. Delete src/config.py, add lib/config.py with completely different content
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    old_content = b"# old config\nDATABASE_URL = 'postgres://localhost/db'\nDEBUG = True\nSECRET_KEY = 'old-secret'\nALLOWED_HOSTS = ['localhost']\nTIMEZONE = 'UTC'\n"
    # Completely rewritten content -- same purpose, different implementation
    new_content = b"# new config system\nimport os\nclass Config:\n    db = os.environ['DB']\n    debug = False\n    key = os.urandom(32)\n    hosts = ['*']\n    tz = 'US/Eastern'\n"

    tree1 = _make_nested_tree(repo, {
        "README.md": b"# Basename Test\n",
        "src/config.py": old_content,
    })
    c1 = _make_commit(repo, tree1, b"Add src/config.py\n", AUTHOR_ALICE, commit_offset=0)

    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Basename Test\n",
        "lib/config.py": new_content,
    })
    c2 = _make_commit(repo, tree2, b"Move config.py from src/ to lib/\n", AUTHOR_ALICE, parents=[c1.id], commit_offset=100)

    repo.refs[b"refs/heads/main"] = c2.id
    repo.refs[b"HEAD"] = c2.id
    repo.close()
    return repo_path


def delete_recreate_repo(tmp_path: Path) -> Path:
    """Create a repo where a file is deleted then re-created in a DIFFERENT commit.

    This should NOT produce a lineage link (different commits = not a rename).

    Commits:
      1. Add data.py
      2. Delete data.py
      3. Add data.py with new content (different commit from delete)
    """
    repo_path = tmp_path
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(repo_path))

    tree1 = _make_nested_tree(repo, {
        "README.md": b"# Delete/Recreate Test\n",
        "data.py": b"original = True\n",
    })
    c1 = _make_commit(repo, tree1, b"Add data.py\n", AUTHOR_ALICE, commit_offset=0)

    tree2 = _make_nested_tree(repo, {
        "README.md": b"# Delete/Recreate Test\n",
    })
    c2 = _make_commit(repo, tree2, b"Delete data.py\n", AUTHOR_ALICE, parents=[c1.id], commit_offset=100)

    tree3 = _make_nested_tree(repo, {
        "README.md": b"# Delete/Recreate Test\n",
        "data.py": b"recreated = True\n",
    })
    c3 = _make_commit(repo, tree3, b"Re-create data.py\n", AUTHOR_ALICE, parents=[c2.id], commit_offset=200)

    repo.refs[b"refs/heads/main"] = c3.id
    repo.refs[b"HEAD"] = c3.id
    repo.close()
    return repo_path
