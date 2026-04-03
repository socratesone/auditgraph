# Implementation Plan: Git Provenance Ingestion

**Branch**: `020-git-provenance-ingestion` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-git-provenance-ingestion/spec.md`

## Summary

Add a deterministic Git provenance ingestion stage to AuditGraph's pipeline. The stage reads local Git history via dulwich (pure Python), materializes Commit, AuthorIdentity, Tag, and Ref nodes into the graph, and links them to existing file entities. A tiered selection algorithm prioritizes structural anchors (tags, root, merges, branch heads, hot-path commits) while filling a configurable budget with high-impact commits scored by file and line change density. CLI and MCP query surfaces expose provenance for developer and agent workflows.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing project)
**Primary Dependencies**: dulwich>=0.22 (pure Python Git library — see [research.md](research.md))
**Storage**: File-based JSON artifacts following existing sharding convention
**Testing**: pytest with synthetic fixture repositories
**Target Platform**: Linux (WSL2), macOS
**Project Type**: Single project — extends existing `auditgraph` package
**Performance Goals**: 10,000+ commit repo ingested within bounded time; Tier 1+2 selection deterministic
**Constraints**: Deterministic output, local-first, no raw payload storage, backward compatible
**Scale/Scope**: Default 1,000 commit budget; Tier 1 unbounded but naturally small (tags + structural anchors)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **DRY** | Pass | Reuses existing hashing, link schema, artifact storage, CLI dispatch, MCP manifest patterns |
| **SOLID — Single Responsibility** | Pass | New `auditgraph/git/` package isolates Git concerns from existing pipeline |
| **SOLID — Open/Closed** | Pass | Pipeline extended via new stage; existing stages unmodified |
| **SOLID — Liskov** | Pass | `run_git_provenance` follows same `StageResult` contract as all other stages |
| **SOLID — Interface Segregation** | Pass | Git query functions are standalone; not forced into existing query interfaces |
| **SOLID — Dependency Inversion** | Pass | dulwich accessed through an adapter; pipeline depends on abstractions (StageResult) |
| **TDD** | Pass | Fixture repositories created first; all code written test-first |
| **YAGNI** | Pass | No speculative features; raw payload storage explicitly excluded |
| **Determinism** | Pass | dulwich is deterministic for same repo state; all IDs content-addressed |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/020-git-provenance-ingestion/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── git-provenance-query.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
auditgraph/
├── git/                         # NEW — Git provenance package
│   ├── __init__.py
│   ├── reader.py                # dulwich adapter: read commits, tags, refs, diffs
│   ├── selector.py              # Tiered commit selection algorithm
│   ├── materializer.py          # Builds entity/link dicts + reverse index from selected commits
│   └── config.py                # Git provenance config schema + defaults
├── pipeline/
│   └── runner.py                # MODIFIED — add run_git_provenance stage + rebuild chain
├── query/
│   ├── git_who.py               # NEW — who changed this file
│   ├── git_log.py               # NEW — commits for a file
│   ├── git_introduced.py        # NEW — earliest commit for a file
│   └── git_history.py           # NEW — combined provenance summary
├── storage/
│   └── hashing.py               # MODIFIED — add git-specific ID functions (commit, author, tag, repo)
├── cli.py                       # MODIFIED — add git-provenance, git-who, git-log, git-introduced, git-history commands
├── config.py                    # MODIFIED — add git_provenance defaults inside profile
└── utils/
    └── mcp_inventory.py         # MODIFIED — add git query tools to inventory

llm-tooling/
└── tool.manifest.json           # MODIFIED — add 4 git query tool definitions

tests/
├── test_git_reader.py           # Unit: dulwich adapter
├── test_git_selector.py         # Unit: tiered selection, scoring, hot/cold paths, Tier 1 exceeds budget
├── test_git_materializer.py     # Unit: entity/link dict construction, ID determinism, reverse index
├── test_git_hashing.py          # Unit: deterministic ID generation (full hex, shard routing)
├── test_git_provenance_stage.py # Integration: full stage with fixture repo, enabled=false skip, missing manifest
├── test_git_queries.py          # Integration: CLI query behavior via reverse index
├── test_git_determinism.py      # Integration: repeated runs produce identical output
├── test_git_edge_cases.py       # Integration: empty repo, root commit, encoding, missing .git, delete/re-create file
└── fixtures/
    └── git/                     # Synthetic repos created by test setup
        └── generate_fixtures.py # Creates deterministic fixture repos via dulwich
```

**Structure Decision**: New `auditgraph/git/` package follows Single Responsibility — all Git-specific logic is isolated. Existing modules receive minimal, additive changes (config defaults, CLI subcommands, pipeline chain). Query modules follow existing `auditgraph/query/` pattern.

## Architecture

### Pipeline Flow

```
run_rebuild:
  1. run_ingest             → file entities created (existing)
  2. run_git_provenance     → NEW: reads .git, selects commits, writes nodes + links
                              Skipped with StageResult(status="skipped") when disabled
  3. run_normalize          → (unchanged)
  4. run_extract            → (unchanged)
  5. run_link               → (unchanged — also creates co-occurrence links)
  6. run_index              → (unchanged — indexes all entities including git types)

Note: run_import does NOT invoke run_git_provenance. Git provenance is repo-scoped,
not file-scoped, and only runs as part of run_rebuild or standalone CLI invocation.
```

### Stage Contract

**Signature**: `run_git_provenance(self, root: Path, config: Config, run_id: str | None = None) -> StageResult`

Mirrors the signature of `run_normalize`, `run_extract`, etc. The stage:
1. Calls `_resolve_run_id(pkg_root, run_id)` to find the latest ingest run
2. Returns `StageResult(stage="git-provenance", status="missing_manifest", detail={"run_id": run_id})` if no ingest manifest exists
3. If `config.profile().get("git_provenance", {}).get("enabled", False)` is falsy, returns `StageResult(stage="git-provenance", status="skipped", detail={"reason": "disabled"})`
4. `run_rebuild` treats `status="skipped"` as non-failing — chain continues to `run_normalize`
5. Reads `ingest-manifest.json` for the file list; reads `.git` via dulwich
6. Computes `inputs_hash = sha256_text(head_commit_sha + ':' + sorted_branch_heads_str + ':' + config_hash)` — includes all branch HEADs so branch advancement produces a new run, preserving determinism
7. Writes entities (Commit, AuthorIdentity, Tag, Ref, Repository) and links via `shard_dir()` + `write_json()`
8. Writes reverse index (`file-commits.json`) to `indexes/git-provenance/`
9. Writes `git-provenance-manifest.json` via `_write_stage_manifest()`
10. Appends replay log entry via `append_text()`

**Dispatch**: Add `"git-provenance"` case to `run_stage()` method in `runner.py`. The CLI `git-provenance` command routes through `run_stage("git-provenance", ...)`. The four query commands (`git-who`, `git-log`, `git-introduced`, `git-history`) call query functions directly, NOT through `run_stage` — consistent with existing query commands like `query`.

### Tiered Selection Algorithm

```
Input: all commits in repo (from dulwich walk)
Output: selected commits for ingestion

Tier 1 — Structural Anchors (always included):
  - All tagged commits
  - Root commit(s) (no parents)
  - Merge commits that are branch points for named branches
  - HEAD of each named branch
  - Any commit touching a hot-path file

Tier 2 — Budget Fill (default 1,000 minus Tier 1 count):
  - For each remaining commit, compute:
    score = files_changed + (lines_changed / 400)
    where files on cold_paths contribute 0
  - Sort by score descending
  - Always include most recent commit + earliest commit (for diff-ability)
  - Fill remaining budget from sorted list
```

### Data Flow

```
dulwich.Repo(root)
  → reader.walk_commits()        # yields raw commit metadata
  → reader.diff_stat(commit)     # files_changed, lines_changed per commit
  → selector.select(commits)     # applies tiered algorithm
  → materializer.build_nodes()   # produces entity dicts
  → materializer.build_links()   # produces link dicts (uses entity_id() for file entity cross-references)
  → materializer.build_reverse_index()  # file_entity_id → [commit_ids] for query performance
  → write via shard_dir() + write_json()  # entities/links to sharded storage
  → write_json(file-commits.json)         # reverse index to indexes/git-provenance/
  → append_text(replay_log)               # records stage completion
```

### Query Flow

```
CLI: auditgraph git-who src/auth.py --root .
  → query/git_who.py:git_who(pkg_root, "src/auth.py")
  → lookup file entity ID via entity_id("file:src/auth.py")
  → read reverse index: indexes/git-provenance/file-commits.json[file_entity_id] → [commit_ids]
  → for each commit_id, load commit entity via load_entity(pkg_root, commit_id)
  → extract authored_by links from adjacency → load author entities
  → return [{author_email, author_names, earliest_commit_date, latest_commit_date, commit_count}]
```

Note: The reverse index (`file-commits.json`) is written by the materializer during
ingestion, avoiding O(n) link directory scans at query time. Query performance is
O(k) where k is the number of commits touching the queried file.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| dulwich over GitPython/pygit2 | Pure Python, no system deps, deterministic, no subprocess injection risk |
| Email as canonical author key | Reduces duplicates while preserving name variants as aliases |
| Tier 1 + Tier 2 selection | Structural anchors are always valuable; budget prevents bloat |
| `files_changed + (lines_changed / 400)` scoring | Prioritizes broad-impact commits while preserving large single-file changes |
| Hot/cold path lists | Configurable priority without changing the core algorithm |
| Link to existing file entities | No duplicate File nodes; uses `entity_id()` directly for cross-reference |
| Full-length SHA-256 IDs | Consistent with `entity_id()` in `storage/hashing.py`; no truncation |
| New stage after ingest | File entities must exist before Git provenance can reference them |
| Tags as first-class nodes | Version milestones are highest-signal provenance anchors |
| Ref/Branch nodes in v1 with inputs_hash fix | All branch HEADs included in inputs_hash — branch advancement produces new run_id, preserving determinism |
| Reverse index for queries | `file-commits.json` avoids O(n) link scans at query time |
| `status="skipped"` for disabled stage | New contract allows conditional stages in rebuild chain without breaking flow |
| Config inside profile | Consistent with `ingestion`, `extraction`; allows per-profile Git provenance settings |
| `max_tier2_commits` naming | Tier 1 is unbounded; config key clarifies what the budget actually governs |
