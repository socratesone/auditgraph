# Tasks: Remove Code Extraction, Narrow Scope to Documents & Provenance

**Input**: Design documents from `/specs/025-remove-code-extraction/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/git-provenance-stage-contract.md, quickstart.md
**Tests**: REQUIRED — TDD is constitutional (`.specify/memory/constitution.md` § III "Test-Driven Development (NON-NEGOTIABLE)") and the spec mandates failing tests before any production code change.
**Organization**: Tasks are grouped by user story per the SDD process. US1 must complete before US3 (deletions are unsafe until file entities have a non-extract creator). US2 and US3 are coupled (docs and deletions land in the same conceptual unit). US4 is validated last.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps task to user story from spec.md (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No project initialization needed — this is a pure modification of an existing package. The "setup" for this spec is just verifying the branch state and confirming the design artifacts are in place.

- [x] T001 Verify current branch is `025-remove-code-extraction` and main is up-to-date: run `git branch --show-current` and confirm output matches; run `git log --oneline main..HEAD` and confirm zero commits ahead.
- [x] T002 Run baseline test suite to capture pre-change state: `python -m pytest tests/ -q --tb=line 2>&1 | tail -5`. Record the passing count and the 3 known pre-existing failures (NER model unavailable × 2, spec011 redaction). This baseline is used to detect regressions later.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational work required. The existing `auditgraph/git/materializer.py` module, `auditgraph/pipeline/runner.py:run_git_provenance` stage, and `auditgraph/storage/hashing.py:entity_id` function are all the foundation US1 needs, and they already exist. Skip directly to user stories.

---

## Phase 3: User Story 1 — `modifies` links resolve to real entities for any file type (Priority: P1) MVP

**Goal**: After the git provenance stage runs, every path referenced by any `modifies` link is materialized as a real `file` entity on disk. The pre-existing dangling-reference bug is fixed. The new `build_file_nodes` function in `auditgraph/git/materializer.py` is the single creator for `file` entities going forward.

**Independent Test**: Run `auditgraph rebuild` against a workspace whose git history touches at least one `.md`, one `.yaml`, and one `.pdf` file. After the rebuild, `auditgraph neighbors <commit_id> --edge-type modifies` returns all three files as resolvable neighbors. Every `to_id` on a `modifies` link resolves to an entity file on disk.

**Plan reference**: This is Phase A in `plan.md`. After this phase, the file entity migration is complete and the project is in an intermediate state where both `extract_code_symbols` AND `build_file_nodes` produce file entities (with matching IDs for overlapping paths). Phase B (US2 + US3) deletes the old creator.

### Tests for User Story 1

> **Write these tests FIRST. Verify they all FAIL before implementing.**

- [x] T003 [P] [US1] Write `test_build_file_nodes_creates_one_entity_per_distinct_path` in `tests/test_git_provenance_file_entities.py`: build a fixture list of `_SelectedCommit` objects (use the same `_make_commit` helper pattern from `tests/test_git_materializer.py`) where 3 commits collectively touch 5 distinct paths; assert `build_file_nodes(commits, repo_path)` returns exactly 5 entity dicts.
- [x] T004 [P] [US1] Write `test_build_file_nodes_dedupes_paths_across_commits` in `tests/test_git_provenance_file_entities.py`: build 4 commits that all touch the same path `foo/bar.md`; assert exactly 1 entity dict is returned.
- [x] T005 [P] [US1] Write `test_build_file_nodes_entity_id_matches_modifies_link_target` in `tests/test_git_provenance_file_entities.py`: build commits with files_changed including path `auditgraph/extract/ner.py`; call `build_file_nodes`; independently call `entity_id("file:auditgraph/extract/ner.py")` from `auditgraph.storage.hashing`; assert one of the returned entities has an `id` field exactly equal to that hash.
- [x] T006 [P] [US1] Write `test_build_file_nodes_entity_has_required_fields` in `tests/test_git_provenance_file_entities.py`: assert each returned entity dict has exactly the keys `{id, type, name, canonical_key, source_path}` and no others; assert `type == "file"`, `name` equals the basename of the path, `canonical_key` equals `f"file:{path}"`, `source_path` equals the path.
- [x] T007 [P] [US1] Write `test_build_file_nodes_is_deterministic` in `tests/test_git_provenance_file_entities.py`: call `build_file_nodes(commits, repo_path)` twice with the same input; assert the two return values are equal (lists of dicts in identical order with identical content).
- [x] T008 [P] [US1] Write `test_build_file_nodes_handles_empty_commit_list` in `tests/test_git_provenance_file_entities.py`: assert `build_file_nodes([], "/tmp/repo") == []`.
- [x] T009 [P] [US1] Write `test_build_file_nodes_handles_paths_with_no_directory` in `tests/test_git_provenance_file_entities.py`: build a commit with `files_changed = ["README.md"]` (no directory prefix); assert the resulting entity has `name == "README.md"` (the whole string is both the basename and the path).
- [x] T010 [P] [US1] Write `test_build_file_nodes_handles_symlink_and_submodule_paths_uniformly` in `tests/test_git_provenance_file_entities.py`: build commits whose `files_changed` lists contain a path that would be a symlink and a path that would be a submodule (just use plausible string paths — the function does not inspect filesystem state); assert both produce file entities with the same schema as regular paths. This locks in the clarification Q2 decision to treat all paths uniformly.
- [x] T011 [US1] Write `test_run_git_provenance_writes_file_entities_to_sharded_storage` in `tests/test_git_provenance_file_entities.py`: set up a `tmp_path` workspace with a real tiny git repo (use the `dulwich` Porcelain API as `tests/test_git_provenance_stage.py` already does), commit 2 files of mixed extensions (`.md` and `.yaml`), call `runner.run_git_provenance(root, config, run_id)`, then walk `pkg_root/entities/<shard>/*.json` and assert that file entities exist for both committed paths.
- [x] T012 [US1] Write `test_run_git_provenance_includes_file_entities_in_outputs_hash` in `tests/test_git_provenance_file_entities.py`: run `run_git_provenance` on a workspace, capture its `outputs_hash` from the stage manifest; modify the workspace to add a new committed file, re-run, capture the new `outputs_hash`; assert the two hashes differ. (This protects replay determinism — adding a file MUST change the hash.)
- [x] T013 [US1] Write `test_modifies_link_targets_resolve_to_real_entities_after_run_git_provenance` in `tests/test_git_provenance_file_entities.py`: run `run_git_provenance` on a fixture workspace; walk every `*.json` file under `pkg_root/links/` and parse it; for every link with `type == "modifies"`, compute the expected entity path from the `to_id` field via `shard_dir(pkg_root / "entities", to_id) / f"{to_id}.json"`; assert that path exists on disk. THIS IS THE LOAD-BEARING ACCEPTANCE TEST FOR US1.
- [x] T014 [US1] Run `python -m pytest tests/test_git_provenance_file_entities.py -v --tb=short` and confirm ALL 11 tests FAIL. The expected failure mode is `ImportError: cannot import name 'build_file_nodes' from 'auditgraph.git.materializer'` (because the function doesn't exist yet). Tests that don't fail at import time should fail at execution because no `file` entity files exist on disk in the test workspaces. Capture the failure summary.

### Implementation for User Story 1

- [x] T015 [US1] Implement `build_file_nodes(selected_commits, repo_path)` in `auditgraph/git/materializer.py`: import `entity_id` (already imported) and the existing helpers; iterate `selected_commits`, walking each commit's `files_changed` list; collect all distinct paths into a `set[str]`; sort the set alphabetically; for each sorted path, build an entity dict `{"id": entity_id(f"file:{path}"), "type": "file", "name": path.rsplit("/", 1)[-1], "canonical_key": f"file:{path}", "source_path": path}`; return the list sorted by entity `id` (matching the determinism convention used by `build_commit_nodes` and friends). Place the function after `build_ref_nodes` and before `build_links`.
- [x] T016 [US1] Run `python -m pytest tests/test_git_provenance_file_entities.py -v -k "build_file_nodes" --tb=short` and confirm the 7 unit tests for the new function PASS (T003 through T010, minus the ones that need stage integration). T011, T012, T013 still fail because the runner hasn't been wired yet.
- [x] T017 [US1] Wire `build_file_nodes` into `auditgraph/pipeline/runner.py:run_git_provenance`: add `build_file_nodes` to the existing `from auditgraph.git.materializer import (...)` import block; in the entity-building section after `build_ref_nodes` is called, add `file_nodes = build_file_nodes(selected.commits, repo_path)`; modify the `all_entities = ...` line to include `+ file_nodes` at the end; verify the entity write loop iterates `all_entities` (it already does — no change needed there).
- [x] T018 [US1] Verify that `stage_outputs_hash` in `run_git_provenance` now picks up file entities automatically. Pre-verified during `/speckit.analyze`: `auditgraph/pipeline/runner.py:432-435` already hashes `sorted(e["id"] for e in all_entities)`. Because T017 adds `file_nodes` to `all_entities`, the file entity IDs are now included in the hash without any code change. This task is a CHECK only — no edit is required. Read the hash calculation in `run_git_provenance`, confirm the `entities` key sources from `all_entities`, and tick this task when the expectation matches the file.
- [x] T019 [US1] Run `python -m pytest tests/test_git_provenance_file_entities.py -v --tb=short` and confirm ALL 11 tests now PASS (Green phase). If any test still fails, investigate and fix before proceeding.
- [x] T020 [US1] Run `python -m pytest tests/test_git_*.py -v --tb=short` and confirm all existing git provenance tests still pass (no regressions in `test_git_materializer.py`, `test_git_edge_cases.py`, `test_git_hashing.py`, `test_git_provenance_stage.py`, `test_git_determinism.py`, `test_git_provenance_name_field.py`).
- [x] T021 [US1] Run the full test suite `python -m pytest tests/ -q --tb=line 2>&1 | tail -10` and confirm: passing count = baseline (from T002) + 11 (the new tests); failing count = 3 (the same pre-existing failures); zero new regressions.

### Manual end-to-end verification (US1)

- [x] T022 [US1] Create a temporary throwaway test workspace `mkdir -p /tmp/spec025-test && cd /tmp/spec025-test && git init && echo "# Test" > README.md && echo "key: value" > config.yaml && git add . && git commit -m "initial"`. Run `cd /home/socratesone/socratesone/auditgraph && rm -rf .pkg && auditgraph init --root /tmp/spec025-test`. Build a temp config that enables git provenance and points include_paths at the test repo. Run `auditgraph rebuild --root /tmp/spec025-test --config /tmp/spec025-config.yaml`. Verify file entities for both `README.md` and `config.yaml` exist on disk and are reachable via `auditgraph neighbors <commit_id> --edge-type modifies`. (This is the human-readable equivalent of T013.)

### Phase A commit checkpoint

- [x] T023 [US1] Stage and commit Phase A changes: `git add auditgraph/git/materializer.py auditgraph/pipeline/runner.py tests/test_git_provenance_file_entities.py`; create commit with message `fix(git-provenance): materialize file entities for all modified paths` referencing FR-001..FR-008 from the spec. **Do NOT push yet.** Phase B is on the same branch and will land before push.

**Checkpoint**: Phase A complete. File entities are now created by both `extract_code_symbols` AND `build_file_nodes` (matching IDs for overlapping paths). The dangling-reference bug is fixed. The project is in a consistent intermediate state and Phase B can begin.

---

## Phase 4: User Story 3 — Dead code and dead config removed (Priority: P2)

**Goal**: Delete `extract_code_symbols.py`, remove the `text/code` parser routing, remove the `chunk_code.enabled` opt-in flag and its tests, and remove the code extensions from default `allowed_extensions`. After this phase, file entities have exactly one creator (`build_file_nodes` from US1) and the project's runtime code carries no references to code extraction.

**Independent Test**: After this phase, grep for `code_symbols`, `chunk_code_enabled`, and `text/code` in `auditgraph/**/*.py` returns zero matches. The full test suite passes (minus the deleted code-chunking tests). A fresh `auditgraph rebuild` on a workspace containing only `.py` files in `include_paths` produces zero entities (the files are skipped at ingest with `unsupported_extension`).

**Note**: US3 is sequenced before US2 in this phase ordering because US2 (documentation) describes the post-deletion state. Doing the deletions first avoids documenting behavior that's about to disappear.

### Tests for User Story 3

> **Write these checks FIRST. They are deletion-confirmation checks rather than new test files. Verify they currently FAIL (because the code still exists), then perform the deletions, then verify they PASS.**

- [x] T024 [US3] Write `test_no_code_symbols_runtime_references_remain` in `tests/test_spec025_scope_invariants.py`: the test asserts that `subprocess.run(["grep", "-rn", "code_symbols", "auditgraph/"], capture_output=True).stdout` (after stripping comment lines) is empty. This test will FAIL until T028 deletes the file and T029 removes the import.
- [x] T025 [US3] Write `test_no_chunk_code_enabled_runtime_references_remain` in `tests/test_spec025_scope_invariants.py`: same pattern, asserting that `chunk_code_enabled` does not appear in any `.py` file under `auditgraph/`. Will FAIL until T031 and T032 strip the config plumbing.
- [x] T026 [US3] Write `test_no_text_code_parser_id_remains` in `tests/test_spec025_scope_invariants.py`: same pattern, asserting `text/code` does not appear in any `.py` file under `auditgraph/`. Will FAIL until T030 strips the parser route and T031 strips the parser branch.
- [x] T027 [US3] Run `python -m pytest tests/test_spec025_scope_invariants.py -v` and confirm all 3 invariant tests FAIL. Capture the failure summary.

### Implementation for User Story 3

- [x] T028 [US3] Delete `auditgraph/extract/code_symbols.py` entirely AND stage the deletion for commit: `git rm auditgraph/extract/code_symbols.py`. Verify with `ls auditgraph/extract/code_symbols.py` (should error: No such file) and `git status --short auditgraph/extract/` (should show `D auditgraph/extract/code_symbols.py`). Using `git rm` directly avoids the I1 ordering problem that arises from using bare `rm` first and then trying to `git rm` an already-absent file in T057.
- [x] T029 [US3] Remove `extract_code_symbols` and its now-dead dependencies from `auditgraph/pipeline/runner.py`. Specifically: (a) delete the `from auditgraph.extract.code_symbols import extract_code_symbols` line (line 22 as of analysis time); (b) change the `from auditgraph.extract.entities import build_entity, build_note_entity` line (line 23) to `from auditgraph.extract.entities import build_note_entity` — the `build_entity` import is now dead because its only caller is being deleted in the next step; (c) in `run_extract`, delete the entire block starting with `code_symbols = extract_code_symbols(root, ok_paths)` through the end of the `for symbol in code_symbols: ...` loop (the loop body calls `build_entity`, which has no other call sites in the project — verified via grep during `/speckit.analyze`). The surrounding note-entity and NER extraction code stays untouched. After the edits, run `grep -rn "build_entity\b" auditgraph/` and confirm zero remaining call sites.
- [x] T029a [US3] Delete the now-dead `build_entity` function from `auditgraph/extract/entities.py`. Per `/speckit.analyze` verification, `build_entity` has exactly one definition (at `entities.py:11`) and one call site (at `runner.py:562` — removed by T029). Leaving the function on disk after T029 would violate the constitutional YAGNI principle ("eliminate speculative abstractions"). Delete the `def build_entity(...)` function body and any helper imports it uniquely used (re-grep after deletion to confirm no dangling imports). `build_note_entity` stays — it has its own call site in `run_extract` via the note extraction branch. After the edit, run `python -c "from auditgraph.extract.entities import build_note_entity; print('ok')"` to confirm the module still imports cleanly.
- [x] T030 [US3] Remove `text/code` from `auditgraph/ingest/policy.py`: in the `PARSER_BY_SUFFIX` dict, delete the 5 lines for `.py`, `.js`, `.ts`, `.tsx`, `.jsx`; in the `DEFAULT_ALLOWED_EXTENSIONS` set, delete the same 5 entries. The file should no longer reference the string `text/code` anywhere.
- [x] T031 [US3] Remove the `text/code` branch and `chunk_code_enabled` reading from `auditgraph/ingest/parsers.py`: locate the `chunkable_parser_ids` block in `parse_file` (lines ~223-233) and replace with the original `if parser_id in ("text/plain", "text/markdown"):` form; verify no reference to `chunk_code_enabled` or `text/code` remains in this file.
- [x] T032 [US3] Remove `chunk_code_enabled` from both `parse_options` construction sites in `auditgraph/pipeline/runner.py`: in `run_ingest` (around line 144) and `run_import` (around line 832), delete the `chunk_code_enabled` key and the `chunk_code_cfg = ...` lookup line that feeds it.
- [x] T033 [US3] Remove code extensions from `auditgraph/config.py:DEFAULT_CONFIG`: in the `allowed_extensions` list under `profiles.<name>.ingestion`, delete `.py`, `.js`, `.ts`, `.tsx`, `.jsx`. Do not touch other entries.
- [x] T034 [US3] Remove code extensions and the chunk_code block from `config/pkg.yaml`: in `profiles.default.ingestion.allowed_extensions`, delete `.py`, `.js`, `.ts`, `.tsx`, `.jsx`; if there is a `profiles.default.ingestion.chunk_code` block, delete it entirely.
- [x] T035 [US3] Delete `tests/test_code_chunking_opt_in.py` entirely AND stage the deletion for commit: `git rm tests/test_code_chunking_opt_in.py`. Verify with `git status --short tests/` (should show `D tests/test_code_chunking_opt_in.py`). Using `git rm` directly for the same reason as T028.
- [x] T036 [US3] Run `python -m pytest tests/test_spec025_scope_invariants.py -v` and confirm all 3 invariant tests now PASS (Green).
- [x] T037 [US3] Run the full test suite `python -m pytest tests/ -q --tb=line 2>&1 | tail -15`. Expected: passing count = baseline (from T002) + 11 (US1 tests) + 3 (US3 invariant tests) − 5 (deleted `test_code_chunking_opt_in.py`); failing count = same 3 pre-existing failures. If any test fails that is NOT one of the 3 known pre-existing failures, investigate before proceeding.

### Manual end-to-end verification (US3)

- [x] T038 [US3] Create a tiny test workspace with one `.py` file in `include_paths`: `mkdir -p /tmp/spec025-pyonly/notes && echo "x = 1" > /tmp/spec025-pyonly/notes/foo.py`. Run `cd /home/socratesone/socratesone/auditgraph && rm -rf .pkg && auditgraph init --root /tmp/spec025-pyonly && auditgraph rebuild --root /tmp/spec025-pyonly`. Verify that the rebuild succeeds, no entities are created (specifically no entity for `foo.py`), and the ingest manifest records `foo.py` with `parse_status: skipped` and `skip_reason: unsupported_extension`. (This confirms FR-FR-015 and the edge case "user attempts to ingest a `.py` file after the change".)

**Checkpoint**: All deletions complete. Code extraction is fully removed from runtime code, config, and tests. Documentation is still stale; US2 fixes that next.

---

## Phase 5: User Story 2 — Documented feature set matches actual behavior (Priority: P1)

**Goal**: Update README.md, QUICKSTART.md, CLAUDE.md, CHANGELOG.md, and `specs/024-document-classification-and-model-selection/NOTES.md` to accurately describe the post-Phase-B state of the project. No claim that auditgraph extracts code symbols. No reference to the deleted `chunk_code.enabled` flag. Explicit statement that source code files are not ingested.

**Independent Test**: A grep for "code symbols" as a feature description in README.md, QUICKSTART.md, and CLAUDE.md returns zero matches. The README's Feature Status table no longer claims code symbol extraction. The QUICKSTART has no "Optional: enable code chunking" section. The CHANGELOG Unreleased section has an entry describing the scope narrowing.

**Note**: US2 is sequenced after US3 because the documentation describes the post-deletion state. Doing the deletions first means the documentation update is one-shot rather than two-shot.

### Documentation tasks

- [x] T039 [P] [US2] Update `README.md` Feature Status table: change the row `| Entity extraction | Implemented | Notes, code symbols |` to `| Entity extraction | Implemented | Notes (markdown), document content. Code files are not ingested — see "Content extraction" below. |`. Change the row `| File ingestion (text, markdown, code) | Implemented | Deterministic with stable IDs |` to `| File ingestion (text, markdown, documents) | Implemented | Deterministic with stable IDs |`.
- [x] T040 [US2] Update `README.md` Content extraction subsection: replace the `- Extracts code symbols from supported source files.` bullet (or whatever the current incorrect wording is) with `- Source code files are not ingested. Files with extensions .py, .js, .ts, .tsx, .jsx are skipped at the ingest stage with reason `unsupported_extension`. For code structure navigation, use a language-aware tool (LSP, ctags, ripgrep, treesitter-based analyzers).`. (Sequential with T039 — both edit `README.md`.)
- [x] T041 [US2] Remove the `#### Code files do not produce chunks` subsection from `README.md` entirely (this was added by the quality sweep and described the now-deleted `chunk_code.enabled` flag). Delete the surrounding paragraph that referenced the opt-in flag. (Sequential with T039 and T040 — all three edit `README.md`.)
- [x] T042 [P] [US2] Update `QUICKSTART.md`: delete the `## Optional: enable code chunking` section in its entirety (the section from the quality sweep that documented the now-removed `ingestion.chunk_code.enabled` flag). Verify the section between this removal and "Common fixes" is contiguous.
- [x] T043 [P] [US2] Update `CLAUDE.md` Common Pitfalls section: remove the `**Code files don't produce chunks by default**:` bullet entirely. Add a new bullet `**Code files are not ingested**: Files with extensions .py, .js, .ts, .tsx, .jsx are skipped at the ingest stage as unsupported_extension. The project deliberately does not provide code intelligence — for that, use language-aware tools (LSP, ctags, ripgrep, treesitter analyzers). The decision is documented in spec 025.`.
- [x] T044 [US2] Update `CLAUDE.md` Project Structure section: in the tree comment for the `extract/` directory, remove the phrase "code symbols" so the comment accurately reflects what's in the directory after T028. The new comment should read something like `extract/                  # entities, NER, ADR, content, document parsers`. (Sequential with T043 — both edit `CLAUDE.md`.)
- [x] T045 [P] [US2] Replace `specs/024-document-classification-and-model-selection/NOTES.md` § 4 ("Code structure understanding is shallow (Issue 2, partial)") with a tombstone paragraph: `### 4. Code structure understanding (rejected as out of scope)\n\nThe original analysis of this section explored adding real code symbol extraction (AST-based, multi-language via tree-sitter). After the verification phase for spec 025, the decision was made to **permanently remove code extraction from auditgraph's scope**. This is not deferred work — it is an explicit scope boundary. Auditgraph is a documents + provenance tool. Code intelligence is a separate problem space served by mature competing tools (LSP, ctags, ripgrep, tree-sitter analyzers, GitHub code search, Sourcegraph, CodeQL). A future sibling project (e.g., \`auditgraph-code\`) could reuse auditgraph's storage format, query layer, and MCP surface to build code intelligence on the same foundation, but that project is not part of this repo's roadmap. See spec 025 for the full reasoning.`. Also delete the § 4 entry from the open questions block (the "Auditgraph's scope on code" question is now resolved as no), the entry from § 4 in the verification questions list (questions 7-9 that pertained to code), and the related items in § 4 of the "When to revisit" section (item 5 if it referenced the scope question).
- [x] T047 [P] [US2] Add an entry to `CHANGELOG.md` under the `## Unreleased` section: include the following content under a `### Removed` and `### Fixed` subsection (create them if they don't exist alongside the existing `### Added` section). `### Removed` content: `- Source code symbol extraction. The extract.code_symbols.v1 rule and its associated module (auditgraph/extract/code_symbols.py) have been deleted. Files with .py, .js, .ts, .tsx, .jsx extensions are no longer ingested by default. The text/code parser_id, the chunk_code.enabled config flag, and tests/test_code_chunking_opt_in.py have all been removed. See spec 025 for the rationale.`. `### Fixed` content: `- Pre-existing dangling-reference bug in git provenance: modifies links now resolve to real file entities for ALL file types (markdown, YAML, PDF, etc.), not just code files. The fix moves file entity creation from the deleted extract_code_symbols extractor into a new build_file_nodes function in auditgraph/git/materializer.py.`.
- [x] T048 [US2] Run `grep -rn "code symbols" README.md QUICKSTART.md CLAUDE.md` and confirm zero matches (other than possibly historical lines in CLAUDE.md "Recent Changes" section, which is exempt per the spec).
- [x] T049 [US2] Run `grep -rn "chunk_code" README.md QUICKSTART.md CLAUDE.md config/pkg.yaml auditgraph/` (excluding test files and `.git`); confirm only matches are in NOTES.md or other historical artifacts, not in user-facing docs or runtime code.
- [x] T050 [US2] Run the full test suite again `python -m pytest tests/ -q --tb=line 2>&1 | tail -10` to confirm the documentation updates didn't accidentally break anything (the test suite shouldn't read docs, but verify anyway).

**Checkpoint**: Documentation aligned with code. The CHANGELOG notes the user-visible behavioral change. No grep of public docs returns "code symbols" as a feature claim.

---

## Phase 6: User Story 4 — Existing workspaces remain queryable after upgrade (Priority: P2)

**Goal**: Validate that an existing workspace produced by a pre-spec-025 version of auditgraph continues to function after upgrade. File entities for paths in git history are re-created with matching IDs. File entities for code files NOT in git history are silently dropped (the documented honest outcome). The migration is non-destructive of user data.

**Independent Test**: Take an existing workspace (or simulate one), run `auditgraph rebuild` after the upgrade, and verify (a) file entities for git-tracked paths exist with the same IDs as before; (b) `auditgraph neighbors` works on commits the same way it did before, just with broader file-type coverage; (c) no error occurs; (d) the CHANGELOG entry is the only "user-visible difference" the upgrade message communicates.

### Verification tasks

- [x] T051 [US4] Write `test_file_entity_id_stable_across_creator_change` in `tests/test_spec025_scope_invariants.py`: this test imports `entity_id` from `auditgraph.storage.hashing` and asserts that `entity_id("file:auditgraph/extract/ner.py")` returns the exact known-good hash `ent_88ad6fe45b1981eb07360e184cafe8ce0c130808a7cb0cff41509edd7228c4f6` (verified empirically during the spec verification phase). This locks in the ID-stability promise for any path that existed before the change. If a future refactor accidentally changes the hashing function, this test catches it.
- [x] T052 [US4] Write `test_workspace_with_only_python_in_include_paths_produces_no_entities` in `tests/test_spec025_scope_invariants.py`: programmatically create a `tmp_path` workspace with `notes/foo.py` (the only file), run `runner.run_ingest(...)` followed by `runner.run_extract(...)`, verify the entity store contains zero entities (confirms FR-015 — code-only workspaces are honestly empty).
- [x] T053 [US4] Run `python -m pytest tests/test_spec025_scope_invariants.py -v` and confirm both new tests pass alongside the 3 invariant tests from US3.
- [x] T054 [US4] Manually exercise the upgrade path on the auditgraph repo itself: ensure `.pkg/` is gone (`rm -rf .pkg`), then run `auditgraph init && auditgraph rebuild --config <config-with-git-prov-enabled>`. Verify (a) the rebuild succeeds, (b) `auditgraph list --type file --count` returns a non-zero number that matches the count of distinct paths in git history, (c) `auditgraph list --type commit --count` returns the expected number of commits, (d) no errors in stderr.

**Checkpoint**: All four user stories validated. The implementation is complete. Move to polish.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final regression check, end-to-end verification on real content, commit Phase B, and prepare the branch for PR.

- [x] T055 Run the complete test suite one final time: `python -m pytest tests/ -v --tb=short 2>&1 | tail -30`. Confirm: (a) total passing count equals baseline + 16 new tests (11 US1 + 3 US3 + 2 US4) − 5 deleted tests; (b) failing count equals exactly the 3 known pre-existing failures (NER model × 2, spec011 redaction); (c) no other failures. If anything else is failing, debug before committing.
- [x] T056 End-to-end on the `example_research.md` test corpus (if still in `notes/`): re-run a clean rebuild with NER enabled and confirm everything still works for the document/provenance happy path. `rm -rf .pkg && auditgraph init --root . && auditgraph rebuild --root . --config /tmp/quality-test.yaml` (the config from the previous quality-sweep session). Verify entities are produced as expected and queries return reasonable results.
- [ ] T057 Stage and commit Phase B. **Note**: the deletions (`code_symbols.py` and `test_code_chunking_opt_in.py`) are already staged by T028 and T035 (both used `git rm`), so this task only needs to stage the *modifications*. Run: `git add auditgraph/extract/entities.py auditgraph/ingest/policy.py auditgraph/ingest/parsers.py auditgraph/pipeline/runner.py auditgraph/config.py config/pkg.yaml tests/test_spec025_scope_invariants.py README.md QUICKSTART.md CLAUDE.md CHANGELOG.md specs/024-document-classification-and-model-selection/NOTES.md` (explicit names only — do not use `git add -A`). Verify with `git status --short` that the staged set contains the 10 modified files plus the 2 already-staged deletions (shown with `D `). Create commit with message `chore(scope): remove code symbol extraction and align documentation` referencing FR-010..FR-027. The commit message should explain that this is the second of two commits on the branch (the first being the Phase A file entity migration committed in T023).
- [ ] T058 Push the branch: `git push --set-upstream origin 025-remove-code-extraction`. Capture the GitHub PR creation URL from the push output for the user to use when opening the PR manually.
- [ ] T059 Verify the branch on GitHub: open the PR creation URL, verify both commits are visible, verify the diff is the expected ~10 source files + ~5 doc files, verify no unrelated files are staged.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **No phase dependencies** — can start immediately.
- **Foundational (Phase 2)** → **No work** — skip.
- **US1 (Phase 3)** → Depends on Setup (T001, T002) only. **MUST complete before US3** because the deletions in US3 are unsafe until file entities have a non-extract creator.
- **US3 (Phase 4)** → Depends on US1 being complete (T023 commit landed locally).
- **US2 (Phase 5)** → Depends on US3 being complete (documents the post-deletion state). Could in principle run in parallel with US3 but risks documenting features that don't exist; sequential ordering is safer.
- **US4 (Phase 6)** → Depends on US3 (deletions need to be in place) and US2 (CHANGELOG needs to exist). Validates the combined post-change state.
- **Polish (Phase 7)** → Depends on all four user stories.

### Within each user story

- TDD ordering is **strict**: tests written first → tests confirmed failing → implementation → tests confirmed passing → full suite regression check.
- Tasks within a story marked `[P]` operate on different files and have no inter-task dependencies, so they can be executed in any order or in parallel.
- Tasks not marked `[P]` have implicit ordering (earlier task must complete before later one).

### Parallel opportunities

- **US1 test writing**: T003-T010 are all `[P]` (different test functions, all in the same new test file but written as independent functions). Can be drafted in parallel.
- **US2 documentation tasks**: T039-T047 are all `[P]` (different files). Can be edited in parallel.
- **US3 invariant tests**: T024-T026 are all `[P]` (independent test functions in the same file).
- **Phase A and Phase B cannot run in parallel**: US1 must complete first.

---

## Implementation Strategy

### MVP First (US1 only)

The MVP is **Phase A complete, no deletions**. After T023, the codebase is in a state where:
- The pre-existing dangling-reference bug is FIXED.
- File entities exist for every file in git history (resolved via `build_file_nodes`).
- The old `extract_code_symbols` is still present but produces duplicate entities with matching IDs (idempotent overwrite of the same on-disk files).
- Every existing test still passes.
- The spec's load-bearing P1 user story (US1) is fully delivered.

This MVP is independently shippable. If for any reason Phases 4-7 had to be deferred (review feedback, time pressure, scope re-litigation), the project would still benefit from the bug fix alone.

### Incremental delivery sequence

1. **Phase A (Commit 1)**: Bug fix + new function. Delivers US1. Ship-ready.
2. **Phase B deletions (Commit 2)**: Removes dead code, deletes the old extractor, updates docs. Delivers US2 + US3. Locks in the scope decision.
3. **Manual verification (no commit)**: Confirms US4 via end-to-end checks. No code change.
4. **Push + PR**: Both commits land together via PR review.

### Test-driven sequencing

Every implementation task is preceded by a test task that drives it. The TDD discipline is enforced by the constitution (`.specify/memory/constitution.md` § III). No implementation task may be marked complete unless its preceding test was first written, run, and confirmed to fail before the implementation, then re-run and confirmed to pass after.

---

## Notes

- **No new dependencies are added.** The new function uses stdlib only and existing project utilities (`entity_id` from `auditgraph.storage.hashing`).
- **The 3 pre-existing test failures are not in scope.** They have been documented across multiple specs and tests as environmental issues (NER spaCy model availability) or unrelated (spec011 redaction). This spec does not touch them.
- **The branch will have exactly 2 commits** before push: T023 (Phase A) and T057 (Phase B). The plan and research docs explicitly reject squashing these into one commit because they have different responsibilities and Phase A is independently valuable.
- **Test fixture compatibility was pre-verified during the plan phase.** The 16 sites in tests that touch `type=file` entities all read fields that the new schema preserves verbatim (`source_path`, `name`, `canonical_key`). No fixture updates needed.
- **The clarification answers from `/speckit.clarify` are load-bearing** — Q1 (schema match exactly) and Q2 (uniform path treatment) determined the implementation shape and are tested explicitly via T006 and T010 respectively.
