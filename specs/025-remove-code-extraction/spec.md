# Feature Specification: Remove Code Extraction, Narrow Scope to Documents & Provenance

**Feature Branch**: `025-remove-code-extraction`
**Created**: 2026-04-07
**Status**: Draft
**Input**: User description: "Remove source code symbol extraction from auditgraph, migrate file entity creation into git provenance to fix pre-existing dangling modifies link targets, narrow project scope to documents and provenance only"

## Clarifications

### Session 2026-04-07

- Q: Does the current `extract_code_symbols` function actually extract symbols (functions, classes, methods, imports)? → No. It creates one opaque `file` entity per source file with four fields (`type`, `name`, `canonical_key`, `source_path`). The rule is named `extract.code_symbols.v1` for an intended behavior that was never implemented. A Python file with 50 functions is the same one node as an empty `__init__.py`.
- Q: Is git provenance currently creating `file` entities for the paths referenced by its `modifies` links? → No. Git provenance writes only 5 entity types to disk: `commit`, `author_identity`, `tag`, `ref`, `repository` (verified at `auditgraph/pipeline/runner.py:392`). Its `modifies` links reference file entity IDs computed via `entity_id(f"file:{path}")` but never materialize the target entities themselves.
- Q: Do the file entity IDs produced by `extract_code_symbols` match those referenced by git provenance's `modifies` links? → Yes. Both code paths derive the ID from `canonical_key = f"file:{normalized_path}"` via the same `entity_id()` function. Verified empirically: both produce `ent_88ad6fe45b1981eb07360e184cafe8ce0c130808a7cb0cff41509edd7228c4f6` for path `auditgraph/extract/ner.py`. The current system relies on this coincidence — `extract_code_symbols` happens to create the entities that git provenance references, but only for the 5 code extensions it recognizes.
- Q: What is the consequence of this coincidence? → A pre-existing dangling-reference bug. Git provenance emits `modifies` links for every file path touched by every commit (markdown, YAML, README, pyproject.toml, configs, code — everything). But file entities exist **only** for the code-extension subset that `extract_code_symbols` processes. Every `modifies` link targeting a non-code file is a dangling reference to a file entity that was never created. `auditgraph neighbors <commit_id>` silently returns empty neighbors for those dangling targets. No test catches this because the tests verify ID derivation consistency but never assert that the referenced entity exists on disk.
- Q: Should auditgraph invest in real code symbol extraction (AST-based, multi-language, via tree-sitter or similar) as a future feature? → No. The decision has been made to scope auditgraph as a documents + provenance tool exclusively. Code intelligence is explicitly out of scope forever, not deferred. Competing tools (Sourcegraph, GitHub code search, CodeQL, tree-sitter-based analyzers, LSP, ctags, tldr) already exist in that space with meaningful investment, and auditgraph's value is in a different niche.
- Q: Should git provenance itself be rolled back? → No. Git provenance answers "who put this document here, when, and what changed?" — that is literal provenance and is the feature that distinguishes auditgraph from any other document ingester. It works identically on repositories of PDFs, markdown notes, and ADRs as it does on code. The fact that earlier test runs happened to target a Python codebase is incidental; nothing about git provenance is inherently coupled to code. Keep it.

### Session 2026-04-07 (clarify pass)

- Q: What schema should new file entities use — match the existing `extract_code_symbols` shape exactly (`source_path` field), introduce a new field name (`path`), keep both, or rename and migrate? → Match the existing schema exactly. New file entities have `id`, `type: "file"`, `name`, `canonical_key`, and `source_path`. Zero migration burden, all existing tests and any downstream readers of `source_path` continue to work without change.
- Q: How should special git objects (symlinks, submodules, etc.) be handled when materializing file entities? → Treat all paths uniformly. Every distinct path string in any commit's `files_changed` list becomes a file entity, regardless of whether it represents a regular file, a symlink, a submodule, a `.gitignore`, or anything else git tracks. The file entity represents "a path git knows about", not "a regular file on disk." No special-casing in v1; richer per-kind treatment can be a follow-on spec if needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — `modifies` links resolve to real entities for any file type (Priority: P1)

As an engineer running git provenance on a workspace of research papers, markdown notes, legal contracts, and occasional code files, when I ask `auditgraph neighbors <commit_id> --edge-type modifies` I get back a complete list of every file the commit touched, regardless of file extension, with each result pointing to a real file entity I can inspect.

**Why this priority**: This is the load-bearing feature that justifies the entire change. Today, git provenance silently produces dangling references for every non-code file in a repository's history. A user inspecting a commit that modified a PDF and a Python file sees only the Python file's neighbor; the PDF neighbor is missing because its file entity was never created. Fixing this is the prerequisite for everything else in this spec — the code extraction removal is safe only after file entities come from a source that covers all file types.

**Independent Test**: Run git provenance against a repository containing a mix of committed file types (at least one `.md`, one `.pdf`, one `.yaml`, one non-code extension, and optionally one code file). After `run_git_provenance` completes, every path that appears in any commit's files-changed list resolves to a file entity on disk. `auditgraph neighbors <commit_id> --edge-type modifies` returns one neighbor per modified file with all target entity IDs resolvable via `auditgraph node <file_entity_id>`.

**Acceptance Scenarios**:

1. **Given** a workspace with commits that touched `README.md`, `config/pkg.yaml`, and `docs/guide.md`, **When** I run the full rebuild pipeline with git provenance enabled, **Then** file entities exist for all three paths and `auditgraph neighbors <commit_id> --edge-type modifies` returns all three as neighbors with resolvable IDs.
2. **Given** a workspace where git history references 500 distinct file paths across all commits, **When** I run the rebuild, **Then** there are exactly 500 `file`-type entities on disk and each one's ID matches `entity_id(f"file:{path}")` for the corresponding path.
3. **Given** a repository with only markdown and PDF files (no code), **When** I run the rebuild with git provenance enabled, **Then** every commit in the history has every one of its modified files reachable via `neighbors --edge-type modifies` with no dangling references.
4. **Given** the same workspace ingested twice, **When** I compare file entity sets, **Then** the two sets are identical in both ID and content (determinism).

---

### User Story 2 — Documented feature set matches actual behavior (Priority: P1)

As a user evaluating whether auditgraph fits my workflow, when I read the README, QUICKSTART, and project documentation, I see an accurate description of what the system does — no claims about extracting code symbols, no references to features that were never implemented, no misleading framing of the project as a code intelligence tool.

**Why this priority**: The current documentation describes auditgraph as extracting "code symbols" from source files, which is false — the extractor produces one opaque file entity per file with no internal structure. A user who reads this and tries to query their code by function name will be confused and frustrated. The README, the Feature Status table, the rule name `extract.code_symbols.v1`, and multiple CLAUDE.md / QUICKSTART passages all propagate the same misleading claim. Fixing the docs without fixing the code is worse than both — it makes the documentation accurate but leaves dead code behind. Fixing both together honors the scope decision cleanly.

**Independent Test**: Read the final README, QUICKSTART, and CLAUDE.md files from top to bottom. Every claim about what auditgraph does maps to a feature that still exists. No phrase claims that functions, classes, methods, or other code symbols are extracted. The phrase "code symbols" does not appear as a feature description. The project is consistently described as a documents + provenance tool.

**Acceptance Scenarios**:

1. **Given** the updated README.md, **When** a new user reads the Features and Feature Status sections, **Then** the word "code symbols" does not appear as a described feature.
2. **Given** the updated README.md Content extraction subsection, **When** a new user reads it, **Then** it describes only the extraction paths that still exist (notes, NER, ADR claims, log claims) and explicitly documents that source code files are not ingested.
3. **Given** the updated QUICKSTART.md, **When** a new user reads it, **Then** there is no "Optional: enable code chunking" section and no reference to `ingestion.chunk_code.enabled`.
4. **Given** the updated CLAUDE.md, **When** a future contributor reads the Common Pitfalls section, **Then** the "Code files don't produce chunks by default" pitfall note is gone and replaced with a note explaining that code extensions are skipped at ingest.

---

### User Story 3 — Dead code and dead config removed (Priority: P2)

As a maintainer of auditgraph, when I browse the codebase, I do not find modules, tests, config knobs, or parser routings for capabilities that the project has explicitly decided not to support. The ingest pipeline does not walk source code files. The extract stage does not invoke a code-symbols extractor. The config does not offer a chunk-code knob. The test suite does not exercise a code-chunking feature that was removed.

**Why this priority**: Dead code is maintenance burden. Every module, test, config field, and parser route that exists but describes a non-feature is a future reader tax. Separately, the `chunk_code.enabled` opt-in flag added during the quality sweep was built to make an off-by-default workaround for the now-deleted capability — with the capability gone, the opt-in is dead code too and should go with it.

**Independent Test**: After the change, the following files do not exist or no longer contain the specified symbols/fields:
- `auditgraph/extract/code_symbols.py` — file deleted entirely
- `auditgraph/pipeline/runner.py` — no import of `extract_code_symbols`, no call site
- `auditgraph/ingest/policy.py` — `PARSER_BY_SUFFIX` does not include `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, and the `text/code` parser_id constant does not appear
- `auditgraph/ingest/parsers.py` — no `text/code` branch, no `chunk_code_enabled` option reference
- `auditgraph/pipeline/runner.py` — no `chunk_code_enabled` key in any `parse_options` construction site
- `config/pkg.yaml` — code extensions removed from `ingestion.allowed_extensions`, `ingestion.chunk_code` block removed entirely
- `auditgraph/config.py` — same removals from `DEFAULT_CONFIG`
- `tests/test_code_chunking_opt_in.py` — file deleted entirely

**Acceptance Scenarios**:

1. **Given** the project after this feature ships, **When** I grep the entire package for `code_symbols`, **Then** the only matches are in git history, spec files documenting the removal, and CLAUDE.md historical notes — no runtime code references.
2. **Given** the project after this feature ships, **When** I grep for `chunk_code`, **Then** the only matches are in spec files and historical notes, not in runtime code, config, or tests.
3. **Given** the full test suite, **When** I run `pytest tests/`, **Then** all currently-passing tests continue to pass, the code-chunking tests have been removed alongside the feature, and the pre-existing unrelated failures (NER model, spec011 redaction) are unchanged.
4. **Given** the project after this feature ships, **When** I run `auditgraph rebuild` on a workspace containing only `.py` files in a directory listed under `include_paths`, **Then** ingest reports 0 files ingested (not a parse failure — a skip with reason `unsupported_extension`) because the code extensions no longer appear in the allowed list.

---

### User Story 4 — Existing workspaces remain queryable after upgrade (Priority: P2)

As a user with an existing `.pkg` workspace produced by a pre-upgrade version of auditgraph that contains code-file entities from the old extractor, when I upgrade to the new version and run `auditgraph rebuild`, my workspace continues to function. Queries against it still return meaningful results. Entities that no longer have a creator are not silently resurrected in a broken state, and the upgrade path is documented so I know what to expect.

**Why this priority**: Backwards compatibility is an explicit constitutional concern for this project. Existing workspaces are live state on user machines. A scope-narrowing change must not break them silently. The honest outcome is that code-file entities from the old extractor disappear on next rebuild (they are no longer produced) — but file entities for paths in git history are recreated with the same IDs by the new git-provenance-backed creator, so existing `modifies` links continue to resolve for anything in git history. The migration cost is bounded: only code files that are NOT in git history lose their entity, and those entities were already of limited value (they carried nothing beyond name and path).

**Independent Test**: Take an existing workspace with file entities from the old extractor (code files, some in git history, some not). Upgrade to the new version and run `auditgraph rebuild`. Verify that:
- File entities for code files that are in git history are re-created by git provenance with identical IDs (same canonical key → same hash)
- File entities for code files NOT in git history are absent from the new graph
- `auditgraph neighbors <commit_id> --edge-type modifies` works for all modified files, not just code files
- Users are warned about this behavior in the release notes / CHANGELOG

**Acceptance Scenarios**:

1. **Given** an existing workspace with file entities and git provenance run, **When** I rebuild after upgrade, **Then** file entities for tracked files (in git history) are re-created with matching IDs and identical content.
2. **Given** a pre-upgrade workspace, **When** I rebuild, **Then** CHANGELOG.md under the Unreleased section documents the scope narrowing, the file-entity migration to git provenance, and the behavioral change for non-git-tracked code files.

---

### Edge Cases

- **Workspace with no git repository**: Git provenance does not run. Since code extraction is also gone, the ingest pipeline produces no file entities at all. `auditgraph list --type file` returns an empty result. This is the honest outcome of the scope decision — if you have no git history and no documents, you have no entities.
- **Workspace with a git repo but git provenance disabled in config**: Same as above — file entities are simply not produced because neither path creates them. This is a visible change: the `file` entity type now requires `git_provenance.enabled: true`.
- **Workspace with commits that touch files that no longer exist on disk (deleted files)**: Git provenance already handles this — it walks commit history, not the working tree. File entities are created for any path that ever appeared in any commit, whether the file currently exists or not. The `modifies` link still points to the same file entity. This matches existing behavior for the reverse index.
- **Very large repositories with thousands of distinct file paths**: Git provenance must deduplicate paths across commits before creating entities so a single path touched by 100 commits becomes 1 entity, not 100. This is already implicit in the current design (the `modifies` link for the same `(commit, file)` pair is idempotent by ID), but the new `build_file_nodes` helper must also dedupe.
- **Rename detection already emits `succeeded_from` links between new and old file entities**: After this change, both endpoints of a rename link still resolve to real entities because git provenance creates file entities for all historical paths, including renamed-away ones. This is an accidental improvement over today's behavior, where the old-path entity was usually dangling.
- **User attempts to ingest a `.py` file after the change**: The ingest stage skips the file with `skip_reason: unsupported_extension`. No error. No warning unless the user opts into verbose logging. The file does not appear in any entity store. This is the intentional end state.
- **User has customized `allowed_extensions` in their profile config to include `.py`**: The ingest stage will still process the file, but no downstream extractor will do anything meaningful with it (no code symbol extraction, no chunking unless markdown). The file will not produce an entity. This is not a regression — the user would have previously gotten a useless one-entity-per-file result, and now they get nothing. The migration note should flag this.
- **Existing workspace has file entities with `source_path` fields but the path no longer matches any git history**: After rebuild, the old file entity remains on disk (we do not sweep orphans in the rebuild flow). This is a pre-existing issue with `auditgraph rebuild` — orphan cleanup is not part of the rebuild contract and this spec does not change that. A full workspace reset (`rm -rf .pkg && auditgraph init && auditgraph rebuild`) would produce a clean state.
- **Symlinks, submodules, and other special git objects**: Treated uniformly with regular files. Each distinct path string returned by the git reader becomes one file entity, regardless of git object kind. A symlink at `notes/shortcut.md` becomes a `file` entity with `source_path: "notes/shortcut.md"`; the entity carries no information about the symlink's target. A submodule at `vendor/somelib` becomes a `file` entity with `source_path: "vendor/somelib"`; the entity carries no information about the submodule's SHA or registered URL. Per-kind richer treatment is out of scope for this spec.

## Constraints

- **Determinism**: The new file-entity creation path MUST produce byte-identical entities across runs for the same git history input. File entity IDs MUST be derived from `canonical_key = f"file:{normalized_path}"` via the existing `entity_id()` function so that the IDs match the `modifies` link targets that git provenance already emits.
- **Local-first**: No new runtime dependencies. The change is pure deletion plus a small addition to an existing in-process module.
- **Backwards compatibility**: File entity IDs for paths that exist in both the old and new creator must match exactly so existing graphs do not experience entity-identity churn on upgrade. The schema of the file entity may be enriched with additional fields (e.g., `path`), but MUST NOT drop any field that existing code reads.
- **Constitutional TDD**: Every behavioral change MUST be driven by a failing test first. The test suite must remain green throughout the implementation phases (not just at the end).
- **No silent data loss**: Any change that removes user-visible capability (e.g., file entities for non-git code files) MUST be documented in CHANGELOG.md under Unreleased and called out in the migration note.
- **Constitutional SOLID — Single Responsibility**: The new `build_file_nodes` function belongs in `auditgraph/git/materializer.py` alongside the other `build_*_nodes` functions. It SHOULD NOT be added to the `extract` module (which is being stripped of code-related code) or to the ingest module (which does not own entity creation).

## Out of Scope (v1)

- **Real code symbol extraction**. This spec is the explicit rejection of that feature. It is not deferred, not future work, not tracked elsewhere in the `specs/` tree beyond a tombstone note in `specs/024-document-classification-and-model-selection/NOTES.md`. If a future version of auditgraph wants code intelligence, it lives in a sibling project (a hypothetical `auditgraph-code`), not in this repo.
- **Tree-sitter integration**. Rejected as part of the same scope decision. No new parser dependencies of any kind in this spec.
- **AST-based or language-aware anything**. Rejected.
- **Call graphs, import resolution, inheritance chains**. Rejected.
- **Per-language chunkers**. Rejected.
- **Rollback of git provenance itself**. Git provenance stays. It is on-mission and the core of this project's value proposition.
- **Deletion of the `file` entity type**. The entity type is preserved; only its creator is moved. `modifies`, `succeeded_from`, and any future link types that reference files continue to work.
- **Orphan entity cleanup in `auditgraph rebuild`**. Existing orphaned file entities from prior runs (from the old extractor) are not automatically deleted. A user who wants a fully clean workspace can manually reset their `.pkg` directory. This behavior is pre-existing and not in scope for this change.
- **Automatic migration of existing workspaces**. No migration script is provided. The rebuild pipeline handles the transition naturally for all data that is in git history; anything outside git history is the user's responsibility.
- **Revisiting the NER extension allowlist**. The NER allowlist (`extraction.ner.natural_language_extensions`) already excludes code extensions and is unaffected by this change.
- **Changing the `ag:note`, `ag:section`, `ag:technology`, `ag:reference`, or any other existing entity type**. This spec does not touch document extraction.

## Requirements *(mandatory)*

### Functional Requirements

#### Git provenance produces file entities

- **FR-001**: System MUST materialize a `file` entity for every distinct file path referenced in the `files_changed` list of any commit processed by the git provenance stage. Path treatment is uniform: symlinks, submodules, regular files, and any other git-tracked path produce file entities the same way. No filtering by git object kind in v1.
- **FR-002**: The file entity MUST have `id`, `type: "file"`, `name` (the file's basename), `canonical_key: "file:<normalized_path>"`, and `source_path` (the full normalized path). The schema MUST match the existing `extract_code_symbols` output shape exactly so existing tests and downstream readers of `source_path` on file entities continue to work without change.
- **FR-003**: File entity IDs MUST be computed via `entity_id(canonical_key)` using the same hashing function that git provenance's `build_links()` uses when constructing `modifies` link target IDs. The two code paths MUST produce identical IDs for the same path, verified by an explicit test.
- **FR-004**: File entity creation MUST be deterministic: the same set of commits MUST produce the same set of file entities with the same IDs and the same content in the same order across runs.
- **FR-005**: File entities MUST be deduplicated before being written: a path touched by 100 commits MUST become 1 entity, not 100.
- **FR-006**: The new file-entity-creating function MUST live in `auditgraph/git/materializer.py` as a new `build_file_nodes(selected_commits, repo_path)` helper, alongside the existing `build_commit_nodes`, `build_author_nodes`, `build_tag_nodes`, `build_repo_node`, and `build_ref_nodes`.
- **FR-007**: The `run_git_provenance` stage MUST call `build_file_nodes` and include its output in the `all_entities` list that is written to the sharded entity store.
- **FR-008**: The git provenance stage manifest's `outputs_hash` MUST include the file entity IDs so replay reproducibility is preserved.

#### Code extraction is removed

- **FR-010**: The file `auditgraph/extract/code_symbols.py` MUST be deleted from the project.
- **FR-011**: The `run_extract` function in `auditgraph/pipeline/runner.py` MUST NOT import from or call `extract_code_symbols`. The corresponding import statement and call site MUST be deleted.
- **FR-012**: The `PARSER_BY_SUFFIX` table in `auditgraph/ingest/policy.py` MUST NOT include `.py`, `.js`, `.ts`, `.tsx`, or `.jsx` entries. The `text/code` parser_id constant MUST NOT appear anywhere in the ingest or extract modules.
- **FR-013**: The `parse_file` function in `auditgraph/ingest/parsers.py` MUST NOT contain any branch that handles `parser_id == "text/code"` or reads any `chunk_code_enabled` option.
- **FR-014**: The `run_ingest` and `run_import` functions in `auditgraph/pipeline/runner.py` MUST NOT include `chunk_code_enabled` in any `parse_options` dict.
- **FR-015**: The `config/pkg.yaml` default config MUST NOT list `.py`, `.js`, `.ts`, `.tsx`, or `.jsx` in `profiles.<name>.ingestion.allowed_extensions`, and MUST NOT contain a `profiles.<name>.ingestion.chunk_code` block.
- **FR-016**: The `DEFAULT_CONFIG` dict in `auditgraph/config.py` MUST NOT list the code extensions in `allowed_extensions` and MUST NOT contain a `chunk_code` entry.
- **FR-017**: The test file `tests/test_code_chunking_opt_in.py` MUST be deleted. Its contents test a feature that no longer exists after this change.

#### Documentation alignment

- **FR-020**: `README.md` MUST NOT claim that auditgraph extracts code symbols. The Feature Status table row for entity extraction MUST NOT reference "code symbols". The File ingestion row MUST describe supported file types accurately (no "code").
- **FR-021**: `README.md` MUST contain an explicit statement that source code files are not ingested, placed near the other extract-stage documentation.
- **FR-022**: `README.md` MUST NOT contain the "Code files do not produce chunks" subsection or any reference to the removed `chunk_code.enabled` opt-in flag.
- **FR-023**: `QUICKSTART.md` MUST NOT contain the "Optional: enable code chunking" section.
- **FR-024**: `CLAUDE.md` MUST NOT contain the "Code files don't produce chunks by default" Common Pitfalls note in its previous form. It MAY contain a replacement note explaining that code extensions are skipped at ingest.
- **FR-025**: `CLAUDE.md` Project Structure section MUST NOT describe the `extract/` module as containing "code symbols" extraction. The module description MUST accurately reflect the modules that remain after deletion.
- **FR-026**: `specs/024-document-classification-and-model-selection/NOTES.md` § 4 ("Code structure understanding is shallow") MUST be replaced with a one-paragraph tombstone that records the scope decision made by this spec and links to this spec's directory.
- **FR-027**: `CHANGELOG.md` Unreleased section MUST include an entry describing the scope narrowing, the deletion of `extract_code_symbols`, the migration of file entity creation into git provenance, the pre-existing dangling-reference bug that this change fixes as a side effect, and the behavioral change that code files are no longer ingested.

#### Preservation of unrelated features

- **FR-030**: Every existing test in the suite that was passing before this change MUST continue to pass after this change, with the exceptions of:
  - Tests deleted because they exercise features removed by this spec (code chunking opt-in tests)
  - Pre-existing failures unrelated to this change (NER test environment issue in `tests/test_ner.py`, spec011 redaction test)
- **FR-031**: Git provenance commit entity creation, author identity creation, ref creation, tag creation, repository creation, and the `modifies` / `authored_by` / `parent_of` / `contains` / `tags` / `on_branch` link types MUST continue to work exactly as they do today. The only change is that the targets of `modifies` links now resolve to real entities for all file types.
- **FR-032**: NER entity extraction, markdown noise stripping, post-extraction filter, and the `natural_language_extensions` allowlist MUST be unchanged by this spec. They already do not depend on code files.
- **FR-033**: Markdown, plain text, PDF, and DOCX ingestion MUST be unchanged. These are the core supported file types and are the entire remaining scope.
- **FR-034**: BM25 indexing, the `list`/`query`/`neighbors` commands from Spec 023, and the MCP tool surface MUST continue to work. Any changes to the `file` entity schema (new `path` field) MUST be additive.

### Key Entities

- **File Entity** (creator changed, schema unchanged): A graph node representing a file path that appears in the repository's git history. The schema is identical to the existing `extract_code_symbols` output: `id`, `type: "file"`, `name` (basename), `canonical_key: "file:<path>"`, and `source_path` (the full normalized path). The only thing this spec changes about the entity is *who* creates it — the git provenance stage takes over from the now-deleted `extract_code_symbols` extractor. No schema migration is required.
- **build_file_nodes** (new): An entity-builder function in `auditgraph/git/materializer.py` that takes a list of selected commits and a repository path, walks each commit's `files_changed` list, deduplicates the union of all referenced paths, and emits one file entity dict per unique path with deterministic ordering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a test workspace containing a git repository with commits that touched at least one markdown file, one YAML file, and one PDF file (and zero code files), running `auditgraph rebuild` with git provenance enabled produces at least one `file` entity per distinct path. `auditgraph neighbors <commit_id> --edge-type modifies` returns all three files as neighbors with resolvable IDs.
- **SC-002**: On a repository containing N distinct file paths across its git history, the number of file entities on disk after rebuild is exactly N, regardless of how many commits touched each path.
- **SC-003**: File entity IDs produced by the new `build_file_nodes` function exactly match the file entity IDs referenced by existing `modifies` link `to_id` values. Verified by a dedicated test.
- **SC-004**: The full project test suite (`pytest tests/ -v`) produces the same number of passing tests as the pre-change baseline minus the 5 deleted code-chunking tests, plus the new file-entity tests. The 3 pre-existing unrelated failures (2 NER, 1 redaction) remain unchanged.
- **SC-005**: A grep of the entire runtime codebase (`auditgraph/**/*.py`) for the string `code_symbols` produces zero matches. A grep for `chunk_code_enabled` produces zero matches. A grep for `text/code` produces zero matches.
- **SC-006**: The README.md, QUICKSTART.md, and CLAUDE.md files contain no claim that auditgraph extracts code symbols. A word search for "code symbols" as a feature description produces zero matches in these files (historical notes in CLAUDE.md Recent Changes sections are exempt).
- **SC-007**: An existing workspace that was produced before this change, when rebuilt with the new version, produces file entities for every path in git history with IDs that match the pre-change entity IDs for any paths that were previously in the workspace.
- **SC-008**: The CHANGELOG.md Unreleased section documents the scope narrowing and the migration, so any future user upgrading through this version sees an explicit note.

## Assumptions

- The git provenance stage's existing `files_changed` data on each `SelectedCommit` object is complete — it lists every file path modified by the commit. If this assumption is wrong, some `modifies` links will still be dangling after the change, but the dangling set will shrink rather than grow compared to today's state.
- The `entity_id()` function in `auditgraph/storage/hashing.py` is deterministic and produces identical output for identical input. This is guaranteed by the project's determinism constraint and is verified empirically elsewhere in the test suite.
- The user has no external tooling or scripts that depend on the existence of `file` entities for code files that are NOT in git history. Such a dependency would break under this change; the migration note documents this.
- No downstream user relies on the `text/code` parser_id constant as part of a plugin or extension point. If they do, their code breaks; the removal is explicit in the CHANGELOG.
- The `chunk_code.enabled` feature added during the quality sweep (Spec 023 follow-up work) has not yet been adopted by any real user. It has existed only briefly and was off by default, so removing it before it is depended on is safe.

## Out of Scope (reiterated for clarity)

- Real code symbol extraction (functions, classes, imports, calls): explicitly rejected as permanent scope boundary. Not future work.
- Tree-sitter or any new parser dependency: rejected.
- Rollback of git provenance: rejected — git provenance is the core on-mission feature.
- Rollback of the `file` entity type itself: rejected — the entity type is preserved; only its creator is relocated.
- Automatic migration scripts: rejected — the rebuild pipeline handles the transition naturally for the common case.
- Orphan entity sweeping on rebuild: rejected — pre-existing concern, not introduced by this change.

## Open Questions

None. The verification phase in the current conversation resolved every design question that would otherwise have been a `[NEEDS CLARIFICATION]` marker. All assumptions and scope decisions are documented above. The spec is ready for `/speckit.plan`.

## Notes

- This spec is intentionally firm about scope. The goal is not to leave a door open for code extraction — the goal is to close that door explicitly and document why, so future contributors do not re-litigate the decision every time a user asks for "can auditgraph find all functions that call X?" The answer is "no, by design; use a code intelligence tool instead."
- The pre-existing dangling-reference bug in git provenance (SC-001, FR-001) was discovered during the verification phase for this spec. It is being fixed incidentally rather than as its own spec because the fix is the same work required to move file entity creation out of `extract_code_symbols`. Splitting them into two specs would duplicate effort.
- The `ca37da1` commit on the now-closed `fix/quality-sweep` branch had a partial README correction that was not included in the PR #36 merge. This spec's documentation update (FR-020 through FR-027) supersedes that partial correction with a more thorough rewrite.
- A future sibling project (`auditgraph-code` or similar) could reuse auditgraph's storage format, query layer (Spec 023), and MCP surface to build code intelligence on the same foundation. That project is not in scope here, and should not be pre-announced with an empty repository. The door is open via architectural reusability; the walk-through happens when someone has a concrete need.
