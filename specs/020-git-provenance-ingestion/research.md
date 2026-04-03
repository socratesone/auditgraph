# Research: Git Provenance Ingestion

**Feature**: 020-git-provenance-ingestion
**Date**: 2026-04-02

## Git Library Selection

### Decision: dulwich

### Rationale
- Pure Python — no C library or system-level Git dependency required
- Deterministic read-only access to local repositories
- Clean API for walking commits, reading trees, parsing diffs
- Supports rename detection via `dulwich.diff_tree.tree_changes` with similarity threshold
- Already widely used in Python tooling (e.g., Poetry uses it)
- No subprocess calls — avoids shell injection surface and platform-dependent Git CLI behavior

### Alternatives Considered

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **dulwich** | Pure Python, no system deps, deterministic | Slightly slower than libgit2 for very large repos | Selected |
| **GitPython** | Familiar API, widely used | Shells out to `git` CLI — non-deterministic across Git versions, subprocess injection risk | Rejected |
| **pygit2** | Fast (libgit2 bindings), full-featured | Requires libgit2 C library — complicates installation, cross-platform issues | Rejected |
| **subprocess + git CLI** | No library dependency | Non-deterministic across Git versions, parsing fragile, security surface | Rejected |

### Dependency Addition
Add `dulwich>=0.22` to `pyproject.toml` dependencies and `requirements-dev.txt`.

---

## Edge Label Naming Convention

### Decision: Lowercase snake_case matching existing link conventions

Existing links use `type: "relates_to"` with `rule_id: "link.source_cooccurrence.v1"`. Git provenance relationships follow the same pattern:

| Relationship | Edge type | Rule ID |
|-------------|-----------|---------|
| Commit TOUCHES File | `modifies` | `link.git_modifies.v1` |
| Commit HAS_PARENT Commit | `parent_of` | `link.git_parent.v1` |
| Commit AUTHORED_BY AuthorIdentity | `authored_by` | `link.git_authored_by.v1` |
| Repository CONTAINS Commit | `contains` | `link.git_contains.v1` |
| Tag POINTS_TO Commit | `tags` | `link.git_tags.v1` |
| Commit ASSOCIATED_WITH Ref | `on_branch` | `link.git_branch.v1` |
| File SUCCEEDED_FROM File | `succeeded_from` | `link.git_lineage.v1` |

Note: Ref/Branch nodes are included in v1. Determinism is preserved by including all branch HEADs in the stage's `inputs_hash` — when any branch advances, a new `run_id` is produced.

---

## File Lineage Confidence Scoring

### Decision: Three-tier confidence based on detection method

| Detection method | Confidence | Scenario |
|-----------------|------------|----------|
| `1.0` (exact) | Git explicitly records rename in tree diff | `git mv` or rename detected by dulwich `tree_changes` with `CHANGE_RENAME` |
| `0.8` (high) | Content similarity >= 70% between deleted and added file | dulwich `tree_changes` with similarity threshold set to 70% |
| `0.6` (moderate) | Same filename in different directories, added and deleted in same commit | Heuristic: `basename(old) == basename(new)` and both in same commit's diff |

Lineage relationships below 0.6 confidence are not created. The threshold is not configurable in v1.

---

## CLI Command Structure

### Decision: Subcommands under existing CLI

| Command | Purpose | Maps to |
|---------|---------|---------|
| `auditgraph git-provenance --root <path>` | Run Git provenance ingestion stage | `run_git_provenance()` |
| `auditgraph git-who <file> --root <path>` | Who changed this file | Query: authors by file |
| `auditgraph git-log <file> --root <path>` | What commits touched this file | Query: commits by file |
| `auditgraph git-introduced <file> --root <path>` | When was this file introduced | Query: earliest commit for file |
| `auditgraph git-history <file> --root <path>` | Full provenance summary | Combined query |

All commands output JSON via `_emit()`.

---

## MCP Tool Structure

### Decision: Mirror CLI commands as MCP tools

| Tool name | Input schema | Maps to CLI |
|-----------|-------------|-------------|
| `git_who_changed` | `{ "file": string }` | `git-who` |
| `git_commits_for_file` | `{ "file": string }` | `git-log` |
| `git_file_introduced` | `{ "file": string }` | `git-introduced` |
| `git_file_history` | `{ "file": string }` | `git-history` |

Added to `tool.manifest.json` and `mcp_inventory.py`.

---

## Deterministic ID Generation

### Decision: Follow existing `entity_id()` convention — full SHA-256 hex digest

All new node IDs use full 64-character hex digests via `sha256_text()`, consistent with the existing `entity_id()` function in `storage/hashing.py`. No truncation.

| Node type | ID format | Canonical key |
|-----------|-----------|---------------|
| Repository | `repo_{sha256_text(repo_path)}` | Workspace root absolute path |
| Commit | `commit_{sha256_text(repo_path + ':' + commit_hex)}` | Repo-scoped to avoid cross-repo collision |
| AuthorIdentity | `author_{sha256_text(repo_path + ':' + email)}` | Email is canonical, repo-scoped |
| Tag | `tag_{sha256_text(repo_path + ':' + tag_name)}` | Tag name is unique within a repo |

File entities reuse existing IDs via `entity_id()` directly — never reimplemented. No new File nodes created by Git provenance. The stage links to existing entities produced by `run_ingest`.

---

## Pipeline Integration Position

### Decision: After `run_ingest`, before `run_normalize`

```
run_rebuild chain:
  run_ingest          → discovers files, creates file entities
  run_git_provenance  → reads Git history, creates commit/author/tag nodes, links to file entities
  run_normalize       → (existing, unchanged)
  run_extract         → (existing, unchanged)
  run_link            → (existing, unchanged — may also create its own links)
  run_index           → (existing, unchanged — indexes all entities including new git types)
```

The stage reads `ingest-manifest.json` to get the list of ingested file paths, then scopes Git history queries to those paths only.
