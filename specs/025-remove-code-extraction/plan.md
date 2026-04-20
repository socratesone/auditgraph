# Implementation Plan: Remove Code Extraction, Narrow Scope to Documents & Provenance

**Branch**: `025-remove-code-extraction` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-remove-code-extraction/spec.md`

## Summary

Two-phase change. **Phase A**: relocate `file` entity creation from `auditgraph/extract/code_symbols.py` into the existing git provenance materializer (`auditgraph/git/materializer.py`) so that every distinct file path touched by any commit is materialized as a `file` entity, fixing the pre-existing dangling-reference bug where git provenance's `modifies` links pointed at file entities that were never created (for any non-code file). **Phase B**: delete `extract_code_symbols.py`, remove `text/code` from the parser routing table, drop the code extensions from the default `allowed_extensions`, delete the `chunk_code.enabled` opt-in flag and its tests, and update README/QUICKSTART/CLAUDE.md/CHANGELOG to reflect the narrowed scope. The two phases land as separate commits on a single branch — Phase A first (so file entities still exist for git provenance consumers when Phase B's deletions land), Phase B second.

## Technical Context

**Language/Version**: Python 3.10+ (existing constraint, no change)
**Primary Dependencies**: stdlib only for the new `build_file_nodes` function. No new dependencies.
**Storage**: Sharded JSON files under `.pkg/profiles/<profile>/` (existing `entities/<shard>/<id>.json` layout, no change)
**Testing**: pytest with `--strict-markers`, flat test directory, fixtures in `tests/fixtures/` (existing convention, no change)
**Target Platform**: Linux (x86_64), macOS (Intel/Apple Silicon) — CLI only (existing constraint)
**Project Type**: Single Python package (`auditgraph/`)
**Performance Goals**: The new `build_file_nodes` pass MUST add no measurable overhead to git provenance — it walks the same `selected_commits` data structure that `build_links()` already iterates, just collecting unique paths into a set. On the auditgraph repo's own ~118-commit history, this is sub-millisecond work compared to the multi-second `git_provenance` stage as a whole.
**Constraints**: Determinism (file entity IDs match `entity_id(f"file:{path}")` exactly so `modifies` link targets resolve), backwards compatibility (existing file entity schema preserved verbatim — clarification Q1 resolved as Option A), local-first (no network), TDD (constitutional, every behavioral change driven by failing test first).
**Scale/Scope**: Auditgraph's own dogfood corpus has 118 commits touching ~140 distinct file paths. Real-world workspaces (e.g., the deferred Epstein dataset) have thousands of commits. The deduplication step in `build_file_nodes` keeps the entity count bounded by distinct paths, not commit count.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| **DRY — Single source of truth** | PASS | After this change, file entities have one creator (`build_file_nodes` in git provenance materializer). Today they have one creator that covers a partial subset (`extract_code_symbols`). The change moves and broadens the source; it does not duplicate. |
| **SOLID — Single Responsibility** | PASS | `build_file_nodes` lives in `auditgraph/git/materializer.py` alongside the other `build_*_nodes` functions. The git provenance stage owns "things that come from the git history", which now correctly includes file entities. The `extract` module is stripped of code-related responsibilities entirely. |
| **SOLID — Open/Closed** | PASS | The change is *deletion* of an extension point (`text/code` parser) and *addition* of an entity type to an existing builder collection. No modification of stable abstractions. |
| **SOLID — Liskov Substitution** | N/A | No inheritance hierarchies are touched. |
| **SOLID — Interface Segregation** | PASS | The new `build_file_nodes` function exposes the same minimal interface as the other `build_*_nodes` functions: takes selected commits + repo path, returns a list of entity dicts. No fat interfaces created. |
| **SOLID — Dependency Inversion** | PASS | The new function depends on `entity_id()` (the abstract hashing function) the same way `build_links()` already does. No new concrete dependencies introduced. |
| **TDD — Tests first** | PASS | Phase A starts with failing tests in a new `tests/test_git_provenance_file_entities.py` that assert file entities exist on disk after `run_git_provenance`. Phase B deletions are also gated on tests: any test that depends on `extract_code_symbols` is itself deleted in the same commit, and any test that asserts file-entity behavior must continue to pass throughout. |
| **Refactoring as first-class** | PASS | This change *is* a refactor: the file entity's creator is being relocated, and dead code is being removed. The cyclomatic complexity of `run_extract` decreases (fewer branches), the cyclomatic complexity of `run_git_provenance` increases by exactly one extra builder call. Net complexity reduction. |
| **YAGNI — Simplicity** | PASS | This is a simplicity-restoring change. The deleted code (`extract_code_symbols.py`, the `chunk_code.enabled` opt-in flag, the `text/code` parser routing) describes capabilities the project has explicitly decided not to support. Removing them is the YAGNI-correct move. |
| **Determinism** | PASS | File entity IDs are derived deterministically via `entity_id(f"file:{path}")`. The `build_file_nodes` function MUST sort its output by entity ID before returning so the entity-write loop in `run_git_provenance` produces deterministic ordering. The dedup step (collecting paths into a set) is the only non-deterministic intermediate; sorting at the end re-establishes ordering. |
| **Backwards compatibility (constitutional + spec constraint)** | PASS | The file entity schema is preserved exactly per clarification Q1. Existing tests that read `source_path` from file entities continue to work. The CHANGELOG entry under Unreleased calls out the user-visible behavioral change (code files no longer ingested) so users upgrading through this version see an explicit note. |

**No violations. No complexity tracking required.**

## Project Structure

### Documentation (this feature)

```text
specs/025-remove-code-extraction/
├── spec.md                      # Feature specification (already exists)
├── plan.md                      # This file
├── research.md                  # Phase 0 output
├── data-model.md                # Phase 1 output
├── quickstart.md                # Phase 1 output
├── contracts/
│   └── git-provenance-stage-contract.md   # Phase 1 output
├── checklists/
│   └── requirements.md          # Quality checklist (already exists)
└── tasks.md                     # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
auditgraph/
├── extract/
│   ├── code_symbols.py          # DELETE entirely
│   ├── content.py               # unchanged
│   ├── entities.py              # unchanged
│   ├── ner.py                   # unchanged
│   └── ...                      # all other extract/ modules unchanged
├── git/
│   └── materializer.py          # MODIFY: add build_file_nodes() helper
├── ingest/
│   ├── policy.py                # MODIFY: remove .py .js .ts .tsx .jsx from PARSER_BY_SUFFIX and DEFAULT_ALLOWED_EXTENSIONS; remove text/code constant
│   └── parsers.py               # MODIFY: remove the text/code branch and chunk_code_enabled option handling
├── pipeline/
│   └── runner.py                # MODIFY: remove extract_code_symbols import + call site in run_extract; add build_file_nodes call in run_git_provenance; remove chunk_code_enabled wiring from both run_ingest and run_import
└── config.py                    # MODIFY: remove .py .js .ts .tsx .jsx from DEFAULT_CONFIG ingestion.allowed_extensions

config/
└── pkg.yaml                     # MODIFY: remove code extensions from ingestion.allowed_extensions; remove ingestion.chunk_code block

tests/
├── test_code_chunking_opt_in.py            # DELETE entirely
├── test_git_provenance_file_entities.py    # NEW: failing tests for FR-001..FR-008
├── test_git_materializer.py                # unchanged (existing assertions about modifies link IDs continue to hold)
├── test_git_edge_cases.py                  # unchanged
└── ...                                     # all other tests unchanged

specs/
└── 024-document-classification-and-model-selection/
    └── NOTES.md                 # MODIFY: replace § 4 with tombstone, remove related open questions

CHANGELOG.md                     # MODIFY: add Unreleased entry
README.md                        # MODIFY: remove "code symbols" claims, add explicit "no code ingestion" note
QUICKSTART.md                    # MODIFY: delete "Optional: enable code chunking" section
CLAUDE.md                        # MODIFY: update Common Pitfalls
```

**Structure Decision**: Single Python package (existing). No new directories. No new test directories. The change is a relocation (one file deleted, one function added) plus dead code removal across 6 source files and 4 documentation files.

## Implementation Phases

### Phase A — Migrate file entity creation into git provenance (Commit 1)

**Goal**: Make `build_file_nodes` exist and produce real file entities for every path in any commit's `files_changed` list. This is the prerequisite for Phase B — Phase B's deletions are unsafe until file entities have a non-extract creator.

**TDD ordering (constitutional)**:

1. **Write failing tests first** (`tests/test_git_provenance_file_entities.py`):
   - `test_build_file_nodes_creates_one_entity_per_distinct_path`
   - `test_build_file_nodes_dedupes_paths_across_commits`
   - `test_build_file_nodes_entity_id_matches_modifies_link_target`
   - `test_build_file_nodes_entity_has_required_fields` (id, type=file, name=basename, canonical_key, source_path)
   - `test_build_file_nodes_is_deterministic` (two calls produce identical output)
   - `test_build_file_nodes_handles_empty_commit_list`
   - `test_build_file_nodes_handles_paths_with_no_directory` (basename equals path)
   - `test_run_git_provenance_writes_file_entities_to_sharded_storage`
   - `test_run_git_provenance_includes_file_entities_in_outputs_hash`
   - `test_modifies_link_targets_resolve_to_real_entities_after_run_git_provenance`
2. **Run the suite** — confirm all 10 fail.
3. **Implement** `build_file_nodes(selected_commits, repo_path)` in `auditgraph/git/materializer.py`. Walk each commit's `files_changed`, dedupe via a set, build entity dicts in the existing schema (`type`, `name`, `canonical_key`, `source_path`) plus the standard `id` derived via `entity_id(f"file:{path}")`, sort the output by ID for determinism, return the list.
4. **Wire it into** `auditgraph/pipeline/runner.py:run_git_provenance` — import `build_file_nodes` alongside the other materializer imports, call it after the other `build_*_nodes` calls, add its output to `all_entities` before the write loop, include the file entity IDs in `stage_outputs_hash`.
5. **Run the failing tests** — confirm all 10 now pass.
6. **Run full suite** — confirm zero regressions.

**Files modified in Phase A**:
- `auditgraph/git/materializer.py` (+1 function, ~25 lines)
- `auditgraph/pipeline/runner.py` (+3 lines: import, call, hash inclusion)
- `tests/test_git_provenance_file_entities.py` (new file, ~150 lines)

**Phase A end state**: file entities are created by both `extract_code_symbols` (for code extensions only) AND `build_file_nodes` (for every git-tracked path). They produce identical IDs for overlapping paths, so no entity-identity churn. The dangling-reference bug is fixed (US1 acceptance scenarios pass). Phase B is now safe to land.

### Phase B — Delete code extraction (Commit 2)

**Goal**: Remove `extract_code_symbols`, remove the `text/code` parser routing, remove the `chunk_code.enabled` opt-in flag, delete the dead test file, update documentation. After Phase B, file entities have exactly one creator (`build_file_nodes`).

**TDD ordering**:

1. **Identify tests that depend on the removed code** — `tests/test_code_chunking_opt_in.py` is the only one. Confirm by grep.
2. **Delete `tests/test_code_chunking_opt_in.py`**. Run the suite — same number of passing tests minus 5 (the deleted ones).
3. **Delete `auditgraph/extract/code_symbols.py`**. Run the suite — expect import errors in `runner.py`.
4. **Remove the import and call site in `auditgraph/pipeline/runner.py:run_extract`**. Run the suite — should be back to green minus 5.
5. **Remove the `chunk_code_enabled` parse_options wiring** from `run_ingest` and `run_import` in `runner.py`. Run the suite — green.
6. **Remove the `text/code` branch in `auditgraph/ingest/parsers.py:parse_file`**. Run the suite — green.
7. **Remove `.py .js .ts .tsx .jsx` from `PARSER_BY_SUFFIX` and `DEFAULT_ALLOWED_EXTENSIONS` in `auditgraph/ingest/policy.py`**. Run the suite — green. Verify any test that ingests `.py` files now expects `skip_reason: unsupported_extension`.
8. **Remove the same code extensions from `auditgraph/config.py:DEFAULT_CONFIG`**. Run the suite — green.
9. **Remove the same code extensions from `config/pkg.yaml`** plus the `ingestion.chunk_code` block. Run the suite — green.
10. **Documentation updates**:
    - `README.md`: Feature Status row, Content extraction subsection, "Code files do not produce chunks" subsection (remove)
    - `QUICKSTART.md`: "Optional: enable code chunking" section (remove)
    - `CLAUDE.md`: Common Pitfalls update, Project Structure description fix
    - `specs/024-document-classification-and-model-selection/NOTES.md`: replace § 4 with tombstone, prune related open questions
    - `CHANGELOG.md`: new Unreleased entry
11. **Run full suite** — green minus the 5 deleted code-chunking tests, plus the 10 new file-entity tests from Phase A. Net: +5 vs the pre-change baseline.
12. **End-to-end smoke test** — fresh `.pkg`, full rebuild on the auditgraph repo with git provenance enabled. Verify file entities exist for non-code files (README.md, config/pkg.yaml, etc.) and that `auditgraph neighbors <commit_id> --edge-type modifies` returns resolvable file entities for all of them.

**Files modified in Phase B**:
- `auditgraph/extract/code_symbols.py` — DELETED
- `auditgraph/pipeline/runner.py` — 3 sites edited
- `auditgraph/ingest/policy.py` — 2 edits (`PARSER_BY_SUFFIX`, `DEFAULT_ALLOWED_EXTENSIONS`)
- `auditgraph/ingest/parsers.py` — 1 edit (remove `text/code` branch)
- `auditgraph/config.py` — 1 edit (`DEFAULT_CONFIG.allowed_extensions`)
- `config/pkg.yaml` — 2 edits (allowed_extensions list, chunk_code block)
- `tests/test_code_chunking_opt_in.py` — DELETED
- `README.md`, `QUICKSTART.md`, `CLAUDE.md`, `CHANGELOG.md`, `specs/024-.../NOTES.md` — documentation

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `build_file_nodes` produces entity IDs that don't match `modifies` link targets | LOW | HIGH | Phase A test `test_build_file_nodes_entity_id_matches_modifies_link_target` asserts the match explicitly. Both code paths derive the ID from the same canonical key string and the same `entity_id()` function — verified empirically during the verification phase. |
| Existing tests that hard-code file entity content (e.g., `tests/support.py`, `tests/test_spec011_export_*`) break under the new schema | LOW | MEDIUM | Clarification Q1 commits us to the existing schema exactly. The new entities have identical fields to the old extractor's output. Any test that read `source_path` continues to work. Verified by listing all tests that touch `type=file` (16 sites; all read `source_path` or just check `type`). |
| Removing `.py` from `allowed_extensions` breaks tests that ingest a `.py` fixture file | MEDIUM | LOW | Grep for tests that ingest `.py` files in fixtures. Such tests would now skip the `.py` file as `unsupported_extension`, which may flip an assertion. Verify and update those tests to use a `.md` fixture instead, OR explicitly add `.py` back via test config. |
| The `chunk_code_enabled` removal breaks some test fixture path | LOW | LOW | Only `tests/test_code_chunking_opt_in.py` references it. That test is being deleted. |
| Documentation lag — README/CHANGELOG say one thing, code does another | LOW | MEDIUM | Phase B tests are gated on the deletions; documentation is updated in the same commit so the two cannot diverge. |
| User has a workspace with `.py` files NOT in git history; loses entities silently | MEDIUM | LOW | Documented in CHANGELOG and the spec's edge cases section. The honest outcome of the scope decision. |
| Spec 020 git provenance test fixtures depend on `extract_code_symbols` having created file entities | LOW | MEDIUM | Inspect `tests/test_git_*.py` fixtures during Phase A. Most assertions check that link `to_id` matches `entity_id(f"file:...")` — they don't require the entity to exist on disk, so they continue to pass. After Phase A, the entities DO exist on disk via `build_file_nodes`, which strengthens those assertions. |

## Dependencies Between Phases

```
Phase A (file entity migration) MUST land before Phase B (deletions).

Phase A delivers value independently:
  - Fixes the pre-existing dangling-reference bug
  - Could ship as its own commit even if Phase B were deferred
  - All existing tests still pass
  - The old extract_code_symbols still runs (creating duplicate file entities
    with matching IDs — same ID = same file on disk = idempotent overwrite)

Phase B depends on Phase A:
  - Once extract_code_symbols is deleted, file entities can ONLY come from
    git provenance.
  - Without Phase A, Phase B would leave the project producing zero file
    entities, breaking US1 (and breaking all 16 tests that touch file
    entities).
```

This is the reason for committing Phase A and Phase B separately on the same branch — Phase A is independently reviewable and could even land independently if Phase B were deferred for any reason.

## Constitution Re-Check (Post-Design)

After working through the implementation phases above, re-evaluating the gates:

| Gate | Re-Check |
|------|----------|
| DRY | Still PASS. Phase A introduces one new function; Phase B removes the duplicate creator. Net: one creator instead of two-with-incomplete-coverage. |
| SOLID — SRP | Still PASS. The new function lives in the right module. |
| TDD | Still PASS. Phase A's TDD ordering is explicit (10 failing tests → implement → 10 passing). Phase B's deletions are gated on test-suite-green at every step. |
| Determinism | Still PASS. The new function sorts its output by entity ID before returning, matching the determinism convention used elsewhere in the project. |
| YAGNI | Still PASS. Net code is reduced (one function added, one entire file + one feature flag + multiple parser branches removed). |

**No new violations. No complexity tracking required.**

## Open Issues for Phase 2 (`/speckit.tasks`)

None. The plan is concrete enough that task generation can proceed without further design questions. The TDD ordering above maps directly to a task list.
