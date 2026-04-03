# Tasks: Git Provenance Ingestion

**Input**: Design documents from `/specs/020-git-provenance-ingestion/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: TDD approach — tests written first per constitution (DrySolidTdd)
**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization, dependency installation, fixture infrastructure

- [x] T001 Add `dulwich>=0.22` to `pyproject.toml` dependencies and `requirements-dev.txt`
- [x] T002 Create `auditgraph/git/__init__.py` package directory
- [x] T003 [P] Add git-specific deterministic ID functions (`commit_id`, `author_id`, `tag_id`, `repo_id`) to `auditgraph/storage/hashing.py` using full `sha256_text()` digest
- [x] T004 [P] Add `git_provenance` config defaults (enabled: false, max_tier2_commits: 1000, hot_paths, cold_paths) inside profile dict in `auditgraph/config.py`
- [x] T005 [P] Create fixture repo generator at `tests/fixtures/git/generate_fixtures.py` using dulwich — must produce deterministic repos covering: linear history, merge commits, multiple authors, file renames, tags (lightweight + annotated), delete/re-create, non-UTF-8 author name, hot/cold path files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on — dulwich adapter, selection algorithm, materializer

**CRITICAL**: No user story work can begin until this phase is complete

### Tests First

- [x] T006 [P] Write failing tests for dulwich reader in `tests/test_git_reader.py` — walk_commits yields correct metadata, diff_stat returns files_changed + lines_changed, tag enumeration, empty repo handling, missing .git error
- [x] T007 [P] Write failing tests for tiered selector in `tests/test_git_selector.py` — Tier 1 anchors always included, Tier 2 scoring formula, hot/cold path filtering, most-recent + earliest always in Tier 2, budget enforcement, Tier 1 exceeds budget produces all Tier 1 + zero Tier 2
- [x] T008 [P] Write failing tests for materializer in `tests/test_git_materializer.py` — entity dict structure matches data-model.md, link dict structure matches link schema, file entity cross-reference uses `entity_id()`, reverse index built correctly, importance_score is -1.0 for Tier 1
- [x] T009 [P] Write failing tests for git ID generation in `tests/test_git_hashing.py` — full hex digest (64 chars), deterministic for same input, shard_dir routes correctly for each prefix type

### Implementation

- [x] T010 Implement dulwich reader adapter in `auditgraph/git/reader.py` — walk_commits(), diff_stat(), list_tags(), list_branches(), repo validation
- [x] T011 Implement tiered commit selector in `auditgraph/git/selector.py` — select() applies Tier 1 + Tier 2 with scoring, hot/cold filtering, budget enforcement
- [x] T012 Implement materializer in `auditgraph/git/materializer.py` — build_nodes() for Commit/AuthorIdentity/Tag/Repository, build_links() for all relationship types using `entity_id()` cross-references, build_reverse_index() for file-commits lookup
- [x] T013 Implement config loader in `auditgraph/git/config.py` — load_git_provenance_config(profile) returning typed config with defaults
- [x] T014 Verify all T006-T009 tests pass

**Checkpoint**: Foundation ready — core git modules work in isolation. User story implementation can begin.

---

## Phase 3: User Story 1 — Ingest Git Commit History (Priority: P1) MVP

**Goal**: `run_git_provenance` stage produces commit, author, tag, and repo nodes from local Git history

**Independent Test**: Ingest fixture repo, verify correct nodes written to sharded storage with deterministic IDs

### Tests First

- [x] T015 [P] [US1] Write failing integration tests in `tests/test_git_provenance_stage.py` — full stage produces expected node count, entities sharded correctly via `shard_dir()`, manifest written, replay log appended, `enabled=false` returns `status="skipped"`, missing ingest manifest returns `status="missing_manifest"`
- [x] T016 [P] [US1] Write failing determinism tests in `tests/test_git_determinism.py` — two runs on same fixture produce identical entity/link files (byte-for-byte hash comparison)

### Implementation

- [x] T017 [US1] Implement `run_git_provenance()` method in `auditgraph/pipeline/runner.py` — signature `(self, root, config, run_id=None)`, resolve run_id, check enabled, read ingest manifest, call reader/selector/materializer, write artifacts via shard_dir, write manifest, append replay log
- [x] T018 [US1] Add `"git-provenance"` case to `run_stage()` dispatch table in `auditgraph/pipeline/runner.py`
- [x] T019 [US1] Insert `run_git_provenance` call into `run_rebuild()` chain in `auditgraph/pipeline/runner.py` — after `run_ingest`, before `run_normalize`, treat `status="skipped"` as non-failing
- [x] T020 [US1] Add `git-provenance` subcommand to `auditgraph/cli.py` — routes through `run_stage("git-provenance", ...)`
- [x] T021 [US1] Verify all T015-T016 tests pass

**Checkpoint**: `auditgraph rebuild` and `auditgraph git-provenance` produce correct git provenance nodes. Deterministic and idempotent.

---

## Phase 4: User Story 2 — File-to-Commit Provenance Relationships (Priority: P1)

**Goal**: Commit TOUCHES File links materialized; reverse index enables file-based lookups

**Independent Test**: Fixture repo with known file-commit relationships; verify links exist and reverse index is correct

### Tests First

- [x] T022 [P] [US2] Add failing tests to `tests/test_git_materializer.py` — modifies links created for each file touched by each commit, link to_id matches `entity_id("file:" + path)`, links written to correct shard dir
- [x] T023 [P] [US2] Add failing tests to `tests/test_git_provenance_stage.py` — reverse index file `indexes/git-provenance/file-commits.json` written, contains correct file_entity_id → [commit_id] mappings

### Implementation

- [x] T024 [US2] Ensure materializer `build_links()` produces `modifies` links with `rule_id: "link.git_modifies.v1"` in `auditgraph/git/materializer.py` (verified — T012 implementation correct)
- [x] T025 [US2] Ensure materializer `build_reverse_index()` writes `file-commits.json` to `indexes/git-provenance/` in `auditgraph/git/materializer.py` (verified — T012 implementation correct)
- [x] T026 [US2] Verify all T022-T023 tests pass

**Checkpoint**: File-to-commit relationships are materialized and queryable via reverse index.

---

## Phase 5: User Story 3 — Author Identity Capture (Priority: P1)

**Goal**: AuthorIdentity nodes created with email as canonical key and name aliases; AUTHORED_BY links connect commits to authors

**Independent Test**: Fixture repo with multiple authors (including same email, different names); verify correct identity nodes and alias lists

### Tests First

- [x] T027 [P] [US3] Add failing tests to `tests/test_git_materializer.py` — same email with different names produces one AuthorIdentity node with sorted name_aliases, authored_by links connect each commit to correct author

### Implementation

- [x] T028 [US3] Verify materializer produces correct AuthorIdentity nodes and authored_by links in `auditgraph/git/materializer.py` (verified — T012 implementation correct, dedup + sorted aliases working)
- [x] T029 [US3] Verify T027 tests pass

**Checkpoint**: Author identities are correctly deduplicated by email with name variants preserved.

---

## Phase 6: User Story 7 — Provenance Queries via CLI (Priority: P1)

**Goal**: CLI commands `git-who`, `git-log`, `git-introduced`, `git-history` return correct provenance data

**Independent Test**: After ingesting fixture repo, run each CLI query and verify JSON output matches expected structure and content per contract schema

### Tests First

**Prerequisite**: T025 (reverse index) and T028 (author links) must be verified green. Reverse index and author-link data must exist in fixture data before query tests can assert correct behavior.

- [x] T030 [P] [US7] Write failing tests in `tests/test_git_queries.py` — `git_who()` returns authors with commit counts and date ranges, `git_log()` returns commits ordered by timestamp desc with `is_merge` and `parent_shas` fields, `git_introduced()` returns earliest commit for file, `git_history()` combines all three plus merge-commit filtering, all queries use reverse index (not link scan), query for non-existent file returns status=error with message

### Implementation

- [x] T031 [P] [US7] Implement `git_who()` in `auditgraph/query/git_who.py` — reads reverse index, loads commit entities, aggregates by author via authored_by links
- [x] T032 [P] [US7] Implement `git_log()` in `auditgraph/query/git_log.py` — reads reverse index, loads commit entities, sorts by authored_at descending
- [x] T033 [P] [US7] Implement `git_introduced()` in `auditgraph/query/git_introduced.py` — reads reverse index, finds earliest commit by authored_at
- [x] T034 [US7] Implement `git_history()` in `auditgraph/query/git_history.py` — composes git_who + git_log + git_introduced
- [x] T035 [US7] Add `git-who`, `git-log`, `git-introduced`, `git-history` subcommands to `auditgraph/cli.py` — each calls query function directly, wraps result via `_emit()`
- [x] T036 [US7] Verify all T030 tests pass

**Checkpoint**: MVP complete — git provenance ingestion + CLI queries functional end-to-end.

---

## Phase 7: User Story 4 — Commit Parent and Merge Structure (Priority: P2)

**Goal**: Parent links and merge commit identification in the graph

**Independent Test**: Fixture repo with merge commits; verify parent_of links and is_merge flag

### Tests First

- [x] T037 [P] [US4] Add failing tests to `tests/test_git_materializer.py` — parent_of links for linear history, multi-parent links for merge commits, is_merge flag true when >1 parent

### Implementation

- [x] T038 [US4] Verify materializer produces correct parent_of links in `auditgraph/git/materializer.py` (may already be in T012 — verify multi-parent handling)
- [x] T039 [US4] Verify T037 tests pass

**Checkpoint**: Merge history is navigable through parent relationships.

---

## Phase 8: User Story 5 — Branch/Ref Context Capture (Priority: P2)

**Goal**: Ref/Branch nodes materialized with head_sha; on_branch links connect commits to refs; all branch HEADs included in inputs_hash for determinism

**Independent Test**: Fixture repo with named branches; verify Ref nodes created, on_branch links exist, and inputs_hash changes when branch HEAD changes

### Tests First

- [x] T059 [P] [US5] Add failing tests to `tests/test_git_materializer.py` — Ref nodes created for each named branch with correct head_sha, on_branch links connect HEAD commit to Ref node
- [x] T060 [P] [US5] Add failing tests to `tests/test_git_determinism.py` — inputs_hash includes branch HEADs; advancing a branch produces a different inputs_hash and run_id

### Implementation

- [x] T061 [US5] Add ref_id() function to `auditgraph/storage/hashing.py` — `ref_{sha256_text(repo_path + ':' + ref_name)}` (already existed from Phase 1 T003)
- [x] T062 [US5] Implement Ref node construction and on_branch link creation in `auditgraph/git/materializer.py`
- [x] T063 [US5] Include sorted branch HEADs in inputs_hash calculation in `auditgraph/pipeline/runner.py` `run_git_provenance()` (updated to branch_name=head_sha format)
- [x] T064 [US5] Verify all T059-T060 tests pass

**Checkpoint**: Branch context is captured deterministically in the graph.

---

## Phase 9: User Story 6 — File Lineage Detection (Priority: P2)

**Goal**: Rename/move lineage detected with confidence metadata

**Independent Test**: Fixture repo with known renames; verify succeeded_from links with correct confidence scores

### Tests First

- [x] T040 [P] [US6] Add failing tests to `tests/test_git_materializer.py` — exact rename produces confidence 1.0, similarity-based rename produces 0.8, basename match produces 0.6, delete/re-create (not rename) produces no lineage link
- [x] T041 [P] [US6] Add failing tests to `tests/test_git_reader.py` — reader.detect_renames() returns rename pairs with detection method using dulwich tree_changes

### Implementation

- [x] T042 [US6] Implement rename detection in `auditgraph/git/reader.py` — detect_renames() using dulwich `tree_changes` with CHANGE_RENAME and similarity threshold 70%
- [x] T043 [US6] Implement basename-match heuristic for delete/add patterns in same commit in `auditgraph/git/reader.py`
- [x] T044 [US6] Wire lineage detection into materializer to produce `succeeded_from` links with confidence metadata in `auditgraph/git/materializer.py`
- [x] T045 [US6] Add lineage data to `git_introduced()` response in `auditgraph/query/git_introduced.py` and `git_history()` in `auditgraph/query/git_history.py`
- [x] T046 [US6] Verify all T040-T041 tests pass

**Checkpoint**: File renames are tracked through the graph with confidence metadata.

---

## Phase 10: User Story 8 — Provenance Queries via MCP (Priority: P2)

**Goal**: Git provenance queries exposed as MCP tools

**Independent Test**: MCP tool list includes git provenance tools; tool invocation returns correct results matching CLI output

### Tests First

- [x] T047 [P] [US8] Add failing tests — tool manifest includes `git_who_changed`, `git_commits_for_file`, `git_file_introduced`, `git_file_history` with correct schemas

### Implementation

- [x] T048 [US8] Add 4 git query tool definitions to `llm-tooling/tool.manifest.json` per contract schema in `contracts/git-provenance-query.yaml`
- [x] T049 [US8] Add tool names to `READ_TOOLS` tuple in `auditgraph/utils/mcp_inventory.py`
- [x] T050 [US8] Verify T047 tests pass

**Checkpoint**: Agents can discover and invoke git provenance queries via MCP.

---

## Phase 11: Edge Cases & Robustness

**Purpose**: Cover all spec edge cases and hardening scenarios

### Tests First

- [x] T051 [P] Write failing edge case tests in `tests/test_git_edge_cases.py`:
  - Empty repository (no commits) → empty provenance, no crash
  - Root commit (no parent) → valid commit node, no parent_of link
  - Non-UTF-8 author name → handled gracefully, no crash
  - Missing/corrupted .git directory → StageResult(status="error") with machine-readable message
  - Extremely large history (mock 100k commits) → bounded by Tier 2 budget, deterministic
  - File deleted and never re-added → file node retains historical commit links
  - Same file path deleted and re-created → no lineage relationship inferred
  - `git-provenance` invoked before `run_ingest` → status="missing_manifest"

### Implementation

- [x] T052 Address any edge case test failures by hardening `auditgraph/git/reader.py`, `selector.py`, and `materializer.py`
- [x] T053 Verify all T051 tests pass

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, full suite validation

- [x] T054 [P] Update `README.md` with git provenance feature description and CLI commands
- [x] T055 [P] Update `QUICKSTART.md` with git provenance setup instructions per `specs/020-git-provenance-ingestion/quickstart.md`
- [x] T056 Run full existing test suite (`python -m pytest tests/ -v`) — all pre-existing tests must still pass (backward compatibility)
- [x] T057 Run all new git provenance tests — full green
- [x] T058 Validate quickstart.md workflow end-to-end on a real repository

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 — Ingest)**: Depends on Phase 2
- **Phase 4 (US2 — File Links)**: Depends on Phase 3 (needs stage working to verify links)
- **Phase 5 (US3 — Authors)**: Depends on Phase 3 (needs stage working to verify identity nodes)
- **Phase 6 (US7 — CLI Queries)**: Depends on Phases 4 + 5 (needs links and authors to query)
- **Phase 7 (US4 — Merge Structure)**: Depends on Phase 3 — can run parallel with Phases 4-6
- **Phase 8 (US5 — Branch/Ref)**: Depends on Phase 3 — can run parallel with Phases 4-7
- **Phase 9 (US6 — Lineage)**: Depends on Phase 3 — can run parallel with Phases 4-8
- **Phase 10 (US8 — MCP)**: Depends on Phase 6 (needs query functions to expose)
- **Phase 11 (Edge Cases)**: Depends on Phase 3 — can run parallel with Phases 4-10
- **Phase 12 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (Ingest)**: Foundation only — no other story dependency
- **US2 (File Links)**: Depends on US1 (needs commit nodes to link from)
- **US3 (Authors)**: Depends on US1 (needs commit nodes to link from)
- **US7 (CLI Queries)**: Depends on US2 + US3 (needs links and authors to query)
- **US4 (Merge)**: Depends on US1 only — independent of US2/US3/US7
- **US5 (Branch/Ref)**: Depends on US1 only — independent of US2/US3/US7
- **US6 (Lineage)**: Depends on US1 only — independent of US2/US3/US7
- **US8 (MCP)**: Depends on US7 (wraps same query functions)

### Within Each Phase

- Tests MUST be written FIRST and MUST FAIL before implementation (constitution mandate)
- Models/hashing before services/materializer
- Core logic before integration (stage wiring)
- Phase complete = all tests green

### Parallel Opportunities

Within Phase 2: T006, T007, T008, T009 all run in parallel (different test files)
Within Phase 6: T031, T032, T033 all run in parallel (different query modules)
Across phases: US4 (Phase 7) and US6 (Phase 8) can run parallel with US2/US3/US7
Within Phase 9: T048, T049 run in parallel (different files)

---

## Parallel Example: Phase 2 (Foundational)

```
# Launch all foundational test files in parallel:
Task T006: test_git_reader.py
Task T007: test_git_selector.py
Task T008: test_git_materializer.py
Task T009: test_git_hashing.py

# Then implement sequentially (reader → selector → materializer):
Task T010: reader.py (independent)
Task T011: selector.py (uses reader output format)
Task T012: materializer.py (uses selector output + reader output)
Task T013: config.py (independent)
```

## Parallel Example: Phase 6 (CLI Queries)

```
# Launch all query module implementations in parallel:
Task T031: git_who.py
Task T032: git_log.py
Task T033: git_introduced.py

# Then compose:
Task T034: git_history.py (depends on T031-T033)
Task T035: cli.py registration (depends on T031-T034)
```

---

## Implementation Strategy

### MVP First (Phases 1-6)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundation (T006-T014)
3. Complete Phase 3: US1 Ingest (T015-T021)
4. Complete Phase 4: US2 File Links (T022-T026)
5. Complete Phase 5: US3 Authors (T027-T029)
6. Complete Phase 6: US7 CLI Queries (T030-T036)
7. **STOP AND VALIDATE**: Full MVP — ingest + query end-to-end
8. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundation → core modules tested in isolation
2. Add US1 (Ingest) → stage runs, nodes written (**first demo**)
3. Add US2 + US3 (Links + Authors) → graph has relationships
4. Add US7 (CLI Queries) → **MVP complete** — developer value delivered
5. Add US4 (Merge) + US6 (Lineage) → enhanced provenance
6. Add US8 (MCP) → agent access
7. Edge cases + Polish → production ready

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Constitution mandates: tests fail first, then implement minimal code to pass
- Commit after each task or logical group
- Total tasks: 64 (T001-T058 + T059-T064)
