---

description: "Task list for feature 028-markdown-extraction: markdown ingestion produces honest, queryable results"
---

# Tasks: Markdown ingestion produces honest, queryable results

**Input**: Design documents from `/specs/028-markdown-extraction/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: **REQUIRED** — Constitution III (Test-Driven Development) is non-negotiable. Every implementation task is preceded by failing tests whose names describe behavior.

**Organization**: Tasks are grouped by user story. User stories within Phase 3+ MAY be delivered in sequence (US1 → US6) to avoid merge conflicts on shared files (`storage/manifests.py`, `pipeline/runner.py`). Stories remain independently testable — each story's failing-then-green test suite proves its acceptance criteria in isolation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US6 (maps to user stories in spec.md)

## Path Conventions

Single Python project, existing layout. Source under `auditgraph/`, tests under `tests/`, shipped config under `config/`, spec docs under `specs/028-markdown-extraction/`. All paths absolute from the repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Promote the already-installed `markdown-it-py` transitive dependency to an explicit declaration so subsequent story test suites can import it reproducibly.

- [X] T001 Add `"markdown-it-py[linkify]>=4,<5"` to the `dependencies` array in `/home/socratesone/socratesone/auditgraph/pyproject.toml` (insert after `jsonschema>=4,<5`). The `[linkify]` extra pulls in `linkify-it-py>=2,<3` which is REQUIRED at runtime for FR-016h bare-URL detection — `.enable("linkify")` is a silent no-op without it. This pin matches the repository's `uv.lock` (which resolves `markdown-it-py==4.0.0` via `rich`). Do not remove any existing dependency. After editing, regenerate `uv.lock` with `uv lock` and verify it now resolves `linkify-it-py` as a top-level entry.
- [X] T001a Add a `[tool.setuptools.package-data]` table to `/home/socratesone/socratesone/auditgraph/pyproject.toml` that bundles `auditgraph/_package_data/**/*.yaml` and `auditgraph/_package_data/**/*.yml` so the shipped wheel includes the rule-pack stubs (per contracts/rule-pack-validator.md). Run `python -m build -w` as an ad-hoc check if available; inspect the resulting wheel to confirm the stubs are packaged.
- [X] T002 Run `make dev` (from repo root) to refresh the dev virtualenv and confirm `markdown-it-py` resolves cleanly at the new pin. Fail loud if the install matrix breaks.
- [X] T003 [P] Create the per-spec fixture directory at `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/` with an empty `__init__.py` (pytest discovery), ready to receive story-specific fixtures. Do NOT populate fixtures here — that happens within each story's task block so fixtures ship with the test file that uses them.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None beyond Phase 1. Every per-story file-touch is captured inside its own user-story phase. The only truly cross-cutting concern is the `storage/manifests.py` dataclass, and per Constitution IV ("no large batch commits") each story adds its own field within that story's phase — enforced by sequencing the stories.

**⚠️ CRITICAL**: User stories MUST land in sequence (US1 → US6) because four of them touch `auditgraph/storage/manifests.py` and three touch `auditgraph/pipeline/runner.py`. Parallelising stories across developers is fine; merging them in random order is not. Rebase each story's branch on the previous story's tip.

**Checkpoint**: `markdown-it-py` is importable; fixture scaffold in place.

---

## Phase 3: User Story 1 — Repeated runs on a markdown corpus keep producing entities (Priority: P1) 🎯 MVP

**Goal**: Fix BUG-1. Separate "parse outcome" from "execution origin" in the ingest record. Cached files reach the extract stage on every rerun.

**Independent Test**: In a workspace with one markdown file, run the pipeline, record entity count N (>0). Run again with no edits. Entity count remains N. Run a third time. Entity count remains N. Also: a pre-028 ingest manifest with `parse_status="skipped"` + `skip_reason="unchanged_source_hash"` produces entities on the next run via the backward-compat reader.

### Tests for User Story 1 (write first, confirm failing)

- [X] T004 [P] [US1] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_ingest_cache_origin.py` exercising `test_cache_hit_sets_parse_status_ok_and_source_origin_cached`, `test_cache_hit_is_consumed_by_extract`, `test_fresh_failed_parse_stays_failed`, `test_unsupported_extension_stays_skipped_and_fresh`. Use the existing `tests.support.null_parse_options()` helper to build a real `Redactor`. Assert against the `IngestRecord` dataclass directly AND against the serialized `ingest-manifest.json` shape.
- [X] T005 [P] [US1] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_backward_compat_reader.py` with a handcrafted legacy-shape `ingest-manifest.json` fixture at `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/legacy_ingest_manifest.json` containing at least one record with `parse_status="skipped"` + `skip_reason="unchanged_source_hash"`. Tests: `test_legacy_cache_hit_normalizes_to_ok_cached`, `test_legacy_true_skip_stays_skipped`, `test_normalizer_does_not_mutate_on_disk_manifest`, `test_normalized_records_are_deterministic_list`.
- [X] T006 [P] [US1] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_invariant_i6_status_origin_orthogonality.py` asserting invariant I6 from data-model.md: `build_source_record` cannot produce `parse_status="failed" + source_origin="cached"`; cached implies ok; failed implies fresh.
- [X] T007 [US1] Run `pytest tests/test_spec028_ingest_cache_origin.py tests/test_spec028_backward_compat_reader.py tests/test_spec028_invariant_i6_status_origin_orthogonality.py -v` and confirm every new test FAILS for the right reason (missing field, missing normalizer, etc.).

### Implementation for User Story 1

- [X] T008 [US1] Extend `IngestRecord` dataclass in `/home/socratesone/socratesone/auditgraph/auditgraph/storage/manifests.py` with `source_origin: str = "fresh"`. Update the `to_dict()` serializer to include the new field. Leave all existing fields untouched.
- [X] T009 [US1] Extend `build_source_record` in `/home/socratesone/socratesone/auditgraph/auditgraph/ingest/sources.py` to accept a keyword-only `source_origin: str = "fresh"` argument. Pass it through to the `IngestRecord` constructor and add it to the returned metadata dict. Preserve the existing positional signature for backward compatibility with existing call sites.
- [X] T010 [US1] Update the cache-hit branch in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` around line 162-175 (inside `run_ingest`). Change `"skipped"` to `"ok"` for `parse_status`, add `source_origin="cached"`, keep `skip_reason=SKIP_REASON_UNCHANGED` and `status_reason=SKIP_REASON_UNCHANGED` for observability. Confirm no other call site was relying on `parse_status="skipped"` for cache hits.
- [X] T011 [US1] Add the backward-compat reader helper `_normalize_ingest_records(records)` in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` (keep it inside the `PipelineRunner` class OR at module level — pick one and stick with it). Logic per contracts/ingest-record-v2.md: translate legacy `parse_status="skipped" + skip_reason in {"unchanged_source_hash", SKIP_REASON_UNCHANGED}` to `parse_status="ok", source_origin="cached"`.
- [X] T012 [US1] Wire `_normalize_ingest_records` into `run_extract` at the top of the function (around current line 565). Both filter sites at lines 567-571 (list comprehension) and 576-578 (for-loop `continue`) now read the normalized list. The filter condition itself (`parse_status != "ok"`) stays verbatim — the fix is upstream of the filter.
- [X] T013 [US1] Update the parallel call sites in `run_import` (`/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` around lines 911-1001) if they have the same cache-hit pattern. Grep for `"skipped"` references inside `run_import` and confirm behavior parity.
- [X] T014 [US1] Audit all existing `parse_status` call sites using `grep -rn "parse_status" auditgraph/ tests/ --include="*.py"` and confirm no other site relies on the old shape (e.g., dashboards that count `"skipped"` records must still see the true-skipped ones, not cache hits). Update comments or counters where the semantic split warrants (e.g., `ingest-manifest.json` can optionally gain a `cached_count` derived from records — out of scope for P1, leave a TODO).
- [X] T015 [US1] Run `pytest tests/test_spec028_ingest_cache_origin.py tests/test_spec028_backward_compat_reader.py tests/test_spec028_invariant_i6_status_origin_orthogonality.py -v` and confirm every test PASSES.
- [X] T016 [US1] Run the full regression suite `pytest tests/ -x -v 2>&1 | tail -50` and confirm no prior passing test has regressed. (Pre-existing failures listed in CLAUDE.md are expected; don't conflate.)
- [X] T017 [US1] Constitution IV refactor audit: re-read the three modified files; confirm no duplication introduced between `run_ingest` and `run_import`; confirm `_normalize_ingest_records` has exactly one call site.

**Checkpoint**: US1 complete. A markdown corpus can be reingested repeatedly and extract keeps producing entities. FR-001 through FR-005 green.

---

## Phase 4: User Story 2 — Markdown documents expose queryable sub-structure (Priority: P1)

**Goal**: Ship `auditgraph/extract/markdown.py` producing `ag:section`, `ag:technology`, `ag:reference` entities and four link types — `contains_section`, `mentions_technology`, `references` (always, section → reference), `resolves_to_document` (internal references only, reference → doc). Deterministic IDs with source-scoped hash inputs, Spec-027 redaction, full integration with the runner.

**Independent Test**: Ingest a fixture with three nested headings, two inline code tokens, one fenced code block, three link styles. Entity store contains one entity per heading, one per distinct code token, one per link target. Run twice: IDs byte-identical.

### Tests for User Story 2 (write first, confirm failing)

- [X] T018 [P] [US2] Create fixture `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/nested_headings.md` with H1 → H2 → H3 → H1 → H2 structure covering ATX and setext headings.
- [X] T019 [P] [US2] Create fixture `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/code_and_links.md` containing inline backticks (`PostgreSQL`, `postgresql`, `Redis`, `postgresql-client`), one fenced code block, one inline link, one reference-style link, one bare URL, and one broken relative link.
- [X] T020 [P] [US2] Create fixture `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/with_secrets.md` containing credential-shaped strings in a heading, a code span, a link target, and a body paragraph. Each secret must be detectable by one of the Spec-027 detectors.
- [X] T021 [P] [US2] Create fixture `/home/socratesone/socratesone/auditgraph/tests/fixtures/spec028/workspace/` with 3 small markdown files that reference each other via relative links (intro.md ↔ setup.md ↔ architecture.md) for cross-document internal-reference testing.
- [X] T022 [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_markdown_sections.py` with tests: `test_single_h1_emits_one_section`, `test_nested_headings_build_parent_chain`, `test_setext_headings_are_captured`, `test_section_name_is_redacted`, `test_section_order_stable_across_runs`, `test_sections_invariant_i5_no_dangling_parents`, `test_section_id_is_source_hash_scoped` (two docs with identical heading paths emit distinct section IDs).
- [X] T023 [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_markdown_technologies.py` with tests: `test_inline_code_emits_technology`, `test_fenced_code_emits_info_string_only` (per FR-016g — body content NOT tokenized), `test_fenced_code_with_empty_info_emits_no_entity`, `test_indented_code_block_emits_no_entity`, `test_casefold_whitespace_dedup_collapses_postgresql_and_postgresql`, `test_postgresql_distinct_from_postgresql_16`, `test_postgresql_distinct_from_postgresql_client`, `test_technology_dedup_is_per_document_not_global`, `test_technology_id_is_source_hash_scoped`, `test_technologies_invariant_i4_unique_canonical_keys`.
- [X] T024 [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_markdown_references.py` with tests: `test_internal_reference_resolves_to_document_id`, `test_external_reference_classified_by_scheme`, `test_autolink_classified_external`, `test_bare_url_in_prose_via_linkify_classified_external`, `test_broken_relative_link_is_unresolved`, `test_fragment_only_link_is_unresolved`, `test_combined_path_and_fragment_classifies_on_path`, `test_query_string_stripped_before_resolution`, `test_directory_or_bare_name_is_unresolved`, `test_mailto_scheme_is_external`, `test_image_emits_no_reference_and_no_technology`, `test_every_reference_has_inbound_references_link`, `test_only_internal_reference_has_outbound_resolves_to_document_link`, `test_references_invariant_i3_internal_targets_exist`.
- [X] T024a [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_markdown_pruning.py` covering FR-016c/FR-016d (invariant I9). Tests: `test_edit_heading_prunes_stale_section_entity`, `test_edit_adds_new_section_without_duplicating_old_one`, `test_pruning_scoped_to_ag_markdown_types_only` (assert `note` entity with the same canonical key is preserved across an edit), `test_pruning_removes_orphan_markdown_links`, `test_pruning_does_not_touch_ner_or_git_provenance_entities`.
- [X] T024c [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_preheading_content.py` covering the pre-heading topology rule (`contracts/markdown-subentities.md` Pre-heading content section). Tests: `test_code_span_before_first_heading_attaches_mentions_technology_to_note`, `test_link_before_first_heading_attaches_references_to_note`, `test_markdown_file_with_no_headings_still_emits_technology_and_reference_entities`, `test_no_headings_file_attaches_all_origin_edges_to_note`, `test_pre_heading_technology_has_deterministic_id_across_runs`.
- [X] T024e [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_document_id_consistency.py` covering adjustments3.md §5. Tests: `test_extract_reads_document_id_from_persisted_payload_not_recomputed` (monkeypatch `deterministic_document_id` to raise; confirm the extractor still runs because it never calls it), `test_record_path_and_document_source_path_and_index_agree` (all three representations of the source path — `record["path"]`, `documents/<doc_id>.json :: source_path`, `DocumentsIndex.by_source_path` — use the same normalized workspace-relative POSIX form).
- [X] T024f [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_opt_out_preserves_existing.py` covering FR-016i (opt-out = preserve existing behavior, the deliberate v1 decision). Tests: `test_disabled_producer_emits_no_new_markdown_subentities` (configure a workspace with `extraction.markdown.enabled: false`, ingest a markdown file that WOULD produce sections/technologies/references, run extract, assert zero new `ag:section`/`ag:technology`/`ag:reference` entities are written); `test_disabled_pruner_does_not_remove_existing_markdown_subentities` (seed a fixture with pre-existing markdown sub-entities on disk — e.g., from a prior run with the flag enabled — then run extract with the flag off; assert the seeded entities are still present); `test_enable_disable_cycle_leaves_prior_entities_on_disk` (run once with flag enabled to produce entities, disable the flag, run again; assert entity count is unchanged because both producer AND pruner are inert per FR-016i); `test_disabled_flag_still_runs_other_producers` (confirm that the opt-out is scoped to markdown sub-entity extraction only — note entity, NER, git-provenance producers continue working). This task closes the FR-016i coverage gap flagged by the post-adjustments3 analyze pass.
- [X] T024d [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_stale_document_artifacts.py` covering adjustments3.md §4. Fixture: a workspace whose `documents/` directory contains a `doc_ghost.json` record for a source path (e.g., `notes/ghost.md`) that is NOT in the current run's ingest manifest (the source file was deleted or excluded). Ingest a different source with a reference to `ghost.md`. Tests: `test_stale_doc_on_disk_does_not_classify_reference_as_internal` (the reference's `resolution` is `unresolved`, `target_document_id` is `null`), `test_stale_doc_does_not_receive_resolves_to_document_link` (no `link.markdown.resolves_to_document.v1` edge terminates at `doc_ghost`), `test_documents_index_by_source_path_excludes_stale_entries` (unit-level: construct an index from a fabricated ingest manifest and assert the stale source_path is absent). This is the regression guard for adjustments3.md §4 and the reviewer-checklist item added per §19.
- [X] T024b [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_cooccurrence_exclusion.py` covering FR-016e (invariant I10). Tests: `test_source_cooccurrence_excludes_ag_section`, `test_source_cooccurrence_excludes_ag_technology`, `test_source_cooccurrence_excludes_ag_reference`, `test_source_cooccurrence_still_emits_for_note_pairs`, `test_no_cooccurrence_link_has_markdown_subentity_on_EITHER_end` (per adjustments3.md §15 — the assertion is EITHER endpoint, NOT just both; a link with one markdown endpoint and one note endpoint is ALSO a violation), `test_mixed_pair_with_one_markdown_subentity_and_one_note_is_rejected`.
- [X] T025 [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_markdown_determinism.py` with tests: `test_two_runs_produce_identical_entity_ids`, `test_two_runs_produce_identical_link_ids`, `test_extract_outputs_hash_stable_across_runs` (invariant I1). Uses the fixture workspace from T021.
- [X] T026 [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_redaction_in_subentities.py` with tests: `test_secret_in_heading_is_redacted`, `test_secret_in_code_span_is_redacted`, `test_secret_in_link_target_is_redacted`, `test_secret_in_section_body_is_redacted`, `test_postcondition_passes_on_fixture_with_secrets` (invariant I2). Uses `with_secrets.md` from T020.
- [X] T027 [US2] Run the twelve new US2 test files as a group and confirm every test FAILS for the right reason (missing module, missing function, missing pruning logic, missing linkify dep, etc.). Explicit invocation — use this command verbatim so no US2 test file is missed:

  ```bash
  pytest -v \
    tests/test_spec028_linkify_runtime.py \
    tests/test_spec028_markdown_sections.py \
    tests/test_spec028_markdown_technologies.py \
    tests/test_spec028_markdown_references.py \
    tests/test_spec028_markdown_pruning.py \
    tests/test_spec028_cooccurrence_exclusion.py \
    tests/test_spec028_preheading_content.py \
    tests/test_spec028_stale_document_artifacts.py \
    tests/test_spec028_document_id_consistency.py \
    tests/test_spec028_opt_out_preserves_existing.py \
    tests/test_spec028_markdown_determinism.py \
    tests/test_spec028_redaction_in_subentities.py
  ```

  If a US2 test file is added after this task is written, append it to this command. The glob pattern `tests/test_spec028_markdown_*.py` misses `linkify_runtime`, `preheading_content`, `stale_document_artifacts`, `document_id_consistency`, `opt_out_preserves_existing`, and `cooccurrence_exclusion` — hence the explicit enumeration.

### Implementation for User Story 2

- [X] T028 [US2] Create `/home/socratesone/socratesone/auditgraph/auditgraph/extract/markdown.py` implementing `extract_markdown_subentities` AND the `DocumentsIndex` dataclass exactly per the public signature in `contracts/markdown-subentities.md`. Structure the internal walker as three private producers: `_emit_sections(tokens, source_path, source_hash, document_id, redactor, pipeline_version)`, `_emit_technologies(tokens, ...)`, `_emit_references(tokens, ..., documents_index)`. ID inputs are source-scoped per data-model.md §1.0. Use `auditgraph.storage.hashing.sha256_text` for ID hashing. Do NOT use `auditgraph.storage.ontology.canonical_key` as the ID input — define the slug rule inline per data-model.md §1.0.
- [X] T029 [US2] Inside `extract_markdown_subentities`, use the authoritative parser setup per `contracts/markdown-subentities.md` "Parser configuration" section: `md = MarkdownIt("commonmark", {"linkify": True}).enable("linkify"); md.parse(text)`. BOTH the constructor option and the rule enable are required (belt-and-suspenders). Wrap in a local adapter function `_tokenize(text) -> list[Token]` so tests can monkeypatch without touching `markdown_it` directly (Constitution II Dependency Inversion). Respect token rules per FR-016g: fenced blocks emit one technology entity keyed on `info` string, empty info → no entity, body content not tokenized.
- [X] T019a [P] [US2] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_linkify_runtime.py` with tests: `test_bare_url_in_prose_emits_link_tokens` (parses `see https://example.com inline` with the authoritative adapter config; asserts at least one `link_open`/`link_close` pair appears in the token stream), `test_linkify_it_py_is_importable` (imports `linkify_it` to fail fast if the dependency went missing), `test_linkify_option_alone_without_rule_noops` AND `test_enable_rule_alone_without_option_noops` (guard tests that document why the spec requires BOTH constructor option AND `.enable("linkify")` — serve as canaries for future markdown-it-py releases that might change this). Place these tests so they run on every CI invocation, not just when the markdown extractor is called.
- [X] T029a [US2] Implement FR-015a — extend `/home/socratesone/socratesone/auditgraph/auditgraph/ingest/parsers.py :: _build_document_metadata` so the returned `payload["document"]` dict carries a `"text"` field holding the redacted full markdown text. This field is ONLY populated when `parser_id == "text/markdown"`; for other parsers the field is absent. Extend the test suite in `tests/test_spec027_*.py` (whichever exercises the document payload) to assert the new field does not break existing Spec-027 redaction tests. Add a new test `tests/test_spec028_document_text_field.py :: test_markdown_document_has_redacted_text_field` to pin the new contract.
- [X] T029b [US2] Implement FR-016b1 cache-migration. Extend the cache-hit branch in `run_ingest` (`runner.py:162-175`) so that, before taking the cache-hit path for a markdown source, it verifies the cached `documents/<doc_id>.json` carries a non-empty `text` field. If missing, fall through to the fresh-parse branch (no `continue` to cache-hit) and record the result as `parse_status="ok"`, `source_origin="fresh"` (NOT `cached`). No warning emitted — this is a silent one-time migration. The check MUST be scoped to `parser_id == "text/markdown"`; non-markdown cache hits MUST be unaffected. Add `tests/test_spec028_cache_migration_document_text.py` with tests: `test_pre028_cache_hit_without_text_triggers_reparse`, `test_post028_cache_hit_with_text_takes_normal_cache_path`, `test_non_markdown_cached_documents_are_unaffected_by_text_check`, `test_migration_run_rewrites_document_payload_with_text` (covers SC-011). This task lands BEFORE T030 (which depends on the `text` field being reliably present in extract).
- [X] T030 [US2] Wire `extract_markdown_subentities` into `run_extract` in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` — insert the call inside the `if parser_id == "text/markdown":` block, after `build_note_entity` (around current line 592). (1) Read `document.text` from the `documents/<doc_id>.json` payload (now populated per T029a) and pass it as `markdown_text`. (2) Read `document.document_id` from the same payload and pass it as `document_id` — do NOT recompute inside the extractor (per adjustments3.md §5 — runner is single source of truth for document identity). (3) Pass the note entity's `id` as `document_anchor_id` so the extractor can attach top-level `contains_section` edges and pre-heading content edges (per adjustments3.md §2 and §3). (4) Build `DocumentsIndex` from the CURRENT RUN's normalized ingest records where `parse_status == "ok"` — NOT from a disk scan of `pkg_root / "documents"` (per adjustments3.md §4 — a disk scan would include stale artifacts from deleted/excluded sources and falsely classify references as internal). For each ok record: open its `documents/<doc_id>.json`, read the authoritative `document_id` and `source_path`, and add both maps (`by_doc_id`, `by_source_path`). Pass the index into every extractor invocation.
- [X] T030a [US2] Implement FR-016c/FR-016d pruning per the algorithm in `data-model.md §5`. In pseudo-code: (1) enumerate entity files under `entities/<shard>/` whose `type ∈ {"ag:section", "ag:technology", "ag:reference"}` AND `refs[0].source_path == <current_source_path>`; collect IDs into `stale_entity_ids`; delete those files. (2) enumerate link files under `links/<shard>/` whose `rule_id ∈ {"link.markdown.contains_section.v1", "link.markdown.mentions_technology.v1", "link.markdown.references.v1", "link.markdown.resolves_to_document.v1"}` AND (`from_id ∈ stale_entity_ids` OR `to_id ∈ stale_entity_ids`); delete those files. Note: the `from OR to` clause catches `contains_section` edges whose from-side is the note entity (not in `stale_entity_ids`) via the to-side match. Link records do NOT carry `source_path`; the algorithm resolves source ownership via entity IDs instead. Extract the pruning into a named helper `_prune_markdown_subentities_for_source(pkg_root, source_path)` to keep runner.py readable. The helper is the ONLY call site that deletes entity/link files; this keeps audit-of-deletions single-source-of-truth.
- [X] T031 [US2] Extend the extract stage's entity/link writing: collect sub-entity links per document into a list, union across documents, and write via the existing `auditgraph.link.write_links(pkg_root, links)`. Add the resulting link paths to `artifacts` (they already participate in `outputs_hash` via the existing `ner_links` pattern — extend that hash input to cover markdown links).
- [X] T031a [US2] Implement FR-016e cooccurrence exclusion in `/home/socratesone/socratesone/auditgraph/auditgraph/link/rules.py :: build_source_cooccurrence_links`. Add a type-exclusion set `EXCLUDED_COOCCURRENCE_TYPES = {"ag:section", "ag:technology", "ag:reference"}`; during candidate-pair enumeration, drop any pair where EITHER endpoint's type is in the exclusion set (per adjustments3.md §15 — not just when both endpoints are in the set). This means a pair like `(note, ag:section)` is excluded, not just `(ag:section, ag:technology)`. Keep the existing `relates_to` type label and rule_id for pairs that survive the filter; existing callers and consumers stay unchanged.
- [X] T032 [US2] Update `run_link` and `run_index` (if needed) to consume the new link types. Check `/home/socratesone/socratesone/auditgraph/auditgraph/link/` to confirm `write_links` is type-agnostic and accepts arbitrary rule IDs; if any type-whitelist exists, extend it. Check `auditgraph/index/type_index.py` to confirm that `ag:section`, `ag:technology`, `ag:reference` register as first-class facets (per Spec-023 the type index is type-agnostic; verify).
- [X] T033 [US2] Add an opt-out config knob per FR-013. Add `extraction.markdown.enabled: true` default to `/home/socratesone/socratesone/auditgraph/config/pkg.yaml` (around line 56, inside the `extraction:` block) and to the default profile literal in `/home/socratesone/socratesone/auditgraph/auditgraph/config.py:59`. Guard the `extract_markdown_subentities` call AND the pruning helper in `run_extract` with this flag — when disabled, both the producer and the pruner stay inert.
- [X] T034 [US2] Run the same twelve US2 test files from T027 (same command, same order) and confirm every test PASSES. Any determinism test failing points at nondeterministic iteration order in the producer — fix at the source, not by sorting in tests. Any linkify-test failing means `linkify-it-py` is missing (check T001 and `uv.lock`).
- [X] T035 [US2] Run `pytest tests/ -x -v 2>&1 | tail -80` and confirm no regression. Pay special attention to Spec-023 type-index tests and Spec-027 postcondition tests.
- [X] T035a [US2] Write and pass `/home/socratesone/socratesone/auditgraph/tests/test_spec028_pre028_workspace_upgrade.py` covering SC-011 end-to-end (US1 × US2 integration) via the INGEST REFRESH path (per adjustments3.md §6 — extract must NOT tolerate a missing `text` field; the migration belongs to ingest). Stage a fixture under `tmp_path` with: (a) a real markdown source file `notes/intro.md` on disk (so ingest can reparse), (b) a pre-028 `.pkg/profiles/default/` tree containing `ingest-manifest.json` with a record for that source carrying `parse_status="skipped"` + `skip_reason="unchanged_source_hash"`, (c) a matching `documents/<doc_id>.json` whose payload LACKS the `text` field (simulating a pre-028 cached record), (d) matching `sources/<source_hash>.json` and `chunks/<shard>/<chk_id>.json` files. Run the full pipeline: `PipelineRunner().run_ingest(...)` followed by `PipelineRunner().run_extract(...)` (or equivalently `run_rebuild`). Assert: (i) ingest treats that source as cache-incomplete, reparses it once, writes a refreshed `documents/<doc_id>.json` that now contains `text`, and records `parse_status="ok"`, `source_origin="fresh"` (NOT `cached`) per FR-016b1; (ii) no warning is emitted for the migration (it is silent by design); (iii) extract then emits at least one `ag:section`, `ag:technology`, or `ag:reference` entity from the refreshed record; (iv) a SECOND back-to-back pipeline run takes the normal cache-hit path (`source_origin="cached"`) — the migration is one-time. Also keep a narrow unit test in `test_spec028_cache_migration_document_text.py` that confirms `run_extract` raises an explicit error when handed an ingest manifest pointing at a markdown document record with missing `text` (per FR-016b2) — this is the negative test that guarantees extract never silently tolerates invalid inputs.
- [X] T036 [US2] Constitution IV refactor audit on `extract/markdown.py`: confirm each of the three private producers has exactly one responsibility; confirm no duplication of ID-hashing logic; confirm `_tokenize` is the only site touching `markdown_it`.

**Checkpoint**: US2 complete. Running the pipeline on a markdown corpus produces queryable sub-entities with deterministic IDs. FR-006 through FR-016 + FR-016a/FR-016b green. MVP milestone hit: US1+US2 together satisfy SC-001, SC-002, SC-003, SC-004, SC-010, SC-011.

---

## Phase 5: User Story 3 — The pipeline loudly reports when it produced nothing (Priority: P2)

**Goal**: Add a structured `warnings[]` field to stage manifests; emit `no_entities_produced` when extract yields zero given nonzero input; emit `empty_index` when index is empty given nonzero entities. Exit codes unchanged.

**Independent Test**: Configure a workspace with one markdown file and disable all entity producers. Run the pipeline. CLI output and persisted manifest contain a structured warning with the correct code. Exit code is 0.

### Tests for User Story 3 (write first, confirm failing)

- [X] T037 [P] [US3] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_throughput_warnings.py` with tests: `test_zero_entities_from_nonzero_input_emits_warning`, `test_one_entity_from_nonzero_input_emits_no_warning`, `test_empty_index_from_nonzero_entities_emits_warning`, `test_warning_persists_to_manifest`, `test_warning_does_not_change_exit_code`, `test_warning_does_not_affect_outputs_hash` (invariant I7 + I8), `test_cli_surfaces_warnings_in_json_output`.
- [X] T038 [US3] Run `pytest tests/test_spec028_throughput_warnings.py -v` and confirm all tests FAIL.

### Implementation for User Story 3

- [X] T039 [US3] Extend `StageManifest` dataclass in `/home/socratesone/socratesone/auditgraph/auditgraph/storage/manifests.py` with `warnings: list[dict[str, str]] = field(default_factory=list)`. Extend `IngestManifest` with the same field. Update `to_dict()` serializers to ALWAYS emit the `warnings` key (even when empty, as `[]`) — per `contracts/stage-manifest-warnings.md` authoritative rule and adjustments3.md §8. Persisted manifests give operators a stable JSON path (`.warnings`) regardless of whether any warnings were emitted. This is asymmetric with the live `StageResult.detail["warnings"]` shape (live MAY omit); do NOT harmonize. Update any dataclass-comparing tests that asserted byte-identity against pre-028 manifests — byte-identity is broken on purpose by the new always-present key.
- [X] T040 [US3] Create `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/warnings.py` exposing the `ThroughputWarning` dataclass and `warning_no_entities`, `warning_empty_index` factory helpers per `contracts/stage-manifest-warnings.md`. Use the exact code/message/hint strings from the contract.
- [X] T041 [US3] Update `_write_stage_manifest` signature in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` (around line 101) to accept `warnings: list[dict[str, str]] | None = None`. Thread it through to the `StageManifest` constructor.
- [X] T042 [US3] Wire warning emission inside `run_extract` in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py`: after the entity list is finalized (around current line 628), compute `upstream_ok = sum(1 for r in normalized_records if r.get("parse_status") == "ok")`; if `upstream_ok >= 1 and len(entity_list) == 0`, append `warning_no_entities(upstream_ok).to_dict()` to a local `warnings` list. Pass `warnings` through to `_write_stage_manifest` and include in `StageResult.detail`.
- [X] T043 [US3] Wire warning emission inside `run_index`: after BM25 is built, if `entities_on_disk >= 1 and bm25_entries == 0`, append `warning_empty_index(entities_on_disk)`. Same pattern as T042.
- [X] T044 [US3] Update `auditgraph/cli.py :: _emit` to pass through `warnings` in the JSON payload when present. Confirm exit code is derived solely from `status`, never from `warnings` (FR-019).
- [X] T045 [US3] Run the US3 test file and confirm all tests PASS. Run the full regression suite and confirm no break.
- [X] T046 [US3] Constitution IV refactor audit: confirm `warning_no_entities` and `warning_empty_index` share the same emit-to-manifest path; confirm no duplication of warning-assembly logic.

**Checkpoint**: US3 complete. FR-017 through FR-020 green. An empty pipeline now surfaces a structured warning without changing exit codes.

---

## Phase 6: User Story 4 — Shipped default configuration never references paths that don't exist (Priority: P2)

**Goal**: Ship schema-valid empty stubs at `config/extractors/core.yaml` and `config/link_rules/core.yaml`; add a rule-pack validator that fails loudly on missing or malformed paths.

**Independent Test**: Fresh install + `auditgraph init` + pipeline run succeeds with no edits. Break the config to reference a nonexistent path — pipeline fails with structured error. Break it to reference a malformed YAML — distinct structured error.

### Tests for User Story 4 (write first, confirm failing)

- [X] T047 [P] [US4] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_rule_pack_validator.py` with tests: `test_default_rule_packs_validate_from_workspace`, `test_default_rule_packs_validate_via_package_resource_fallback`, `test_missing_path_raises_rule_pack_error_missing`, `test_malformed_yaml_raises_rule_pack_error_malformed`, `test_absolute_path_resolves_verbatim`, `test_empty_list_is_valid`, `test_relative_path_resolves_against_workspace_root`, `test_error_kind_distinguishes_missing_vs_malformed`.
- [X] T047a [P] [US4] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_init_copies_stubs.py` exercising `initialize_workspace` against a fresh `tmp_path`. Tests: `test_init_creates_pkg_yaml`, `test_init_creates_extractors_stub`, `test_init_creates_link_rules_stub`, `test_init_is_idempotent_on_existing_stub` (pre-seed one stub, confirm it's not overwritten), `test_init_stub_content_matches_package_resource_byte_identically`.
- [X] T048 [P] [US4] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_rule_pack_cli_integration.py` exercising a full `auditgraph rebuild` invocation with (a) default config (exit 0), (b) config referencing missing path (exit 5, structured JSON on stdout or stderr), (c) config referencing malformed YAML (exit 5 with distinct `code`).
- [X] T049 [US4] Run the three new US4 test files and confirm ALL FAIL.

### Implementation for User Story 4

- [X] T050 [US4] Create the shipped package-resource stub at `/home/socratesone/socratesone/auditgraph/auditgraph/_package_data/config/extractors/core.yaml` with exactly the content from `contracts/rule-pack-validator.md` ("Shipped defaults and init behavior" section). Empty but schema-versioned. Also mirror the file into the repo's top-level `/home/socratesone/socratesone/auditgraph/config/extractors/core.yaml` so editable installs see it at the path `pkg.yaml` already references.
- [X] T051 [US4] Create the shipped package-resource stub at `/home/socratesone/socratesone/auditgraph/auditgraph/_package_data/config/link_rules/core.yaml` with exactly the content from `contracts/rule-pack-validator.md`. Mirror into `/home/socratesone/socratesone/auditgraph/config/link_rules/core.yaml`.
- [X] T051a [US4] Create `/home/socratesone/socratesone/auditgraph/auditgraph/_package_data/__init__.py` (empty) so Python treats `_package_data` as a package (required for `importlib.resources.files("auditgraph") / "_package_data"` to work). Confirm `pyproject.toml`'s existing `[tool.setuptools.packages.find] include = ["auditgraph*"]` picks up the new subpackage.
- [X] T052 [US4] Create `/home/socratesone/socratesone/auditgraph/auditgraph/utils/rule_packs.py` exposing `RulePackError` (frozen dataclass subclassing `Exception`) and `validate_rule_pack_paths(paths, workspace_root)` exactly per `contracts/rule-pack-validator.md`. Use `yaml.safe_load` — never `yaml.load`. Implement the package-resource fallback: when a declared path does not exist under `workspace_root`, look it up under `importlib.resources.files("auditgraph") / "_package_data" / <declared_path>` before raising `RulePackError(kind="missing")`. **CRITICAL**: the parameter is `workspace_root` (the directory containing `config/pkg.yaml`), NOT the config file's parent — using the config-file parent reintroduces the `config/config/...` path-doubling bug from adjustments2.md §4.
- [X] T053 [US4] Wire the validator into `/home/socratesone/socratesone/auditgraph/auditgraph/config.py`. Add `_validate_profile_rule_packs(profile, workspace_root)` and call it from the point `Config.profile()` materializes the profile dict. Pass `workspace_root` (the directory containing `config/pkg.yaml`), NOT the config file's parent — this avoids the `config/config/...` path-doubling bug diagnosed in adjustments2.md §4. Update the `auditgraph/cli.py` config-load call sites to thread the workspace root through.
- [X] T054 [US4] Update `auditgraph/cli.py` to catch `RulePackError` at the top-level dispatch and emit the structured JSON error envelope from `contracts/rule-pack-validator.md` with exit code 5. Follow the Spec-027 `Neo4jTlsRequiredError` pattern.
- [X] T054a [US4] Update `/home/socratesone/socratesone/auditgraph/auditgraph/scaffold.py :: initialize_workspace` so it copies the two stub rule-packs alongside `pkg.yaml`. Source for the copy is `importlib.resources.files("auditgraph") / "_package_data" / "config" / "extractors" / "core.yaml"` and the matching `link_rules` path. Destination is `<root>/config/extractors/core.yaml` and `<root>/config/link_rules/core.yaml`. Idempotency rule: if the destination already exists, skip (match the existing behavior for pkg.yaml at scaffold.py:25-28). Append each newly created file path to the `created` list returned by the function.
- [X] T055 [US4] Confirm packaging: the `[tool.setuptools.package-data]` table added in T001a includes the new stub files. Run `python -m build -w` (if the dev environment has `build` installed) and inspect the resulting wheel (`unzip -l dist/*.whl | grep _package_data`) to verify the YAML stubs are bundled. If `build` is not available, document the manual verification steps in a code comment near the package-data declaration and move on — CI will catch regressions.
- [X] T056 [US4] Run the three US4 test files and confirm ALL PASS. Run full regression — the shipped stubs must not break any test that invokes `auditgraph init` or loads the default config.
- [X] T057 [US4] Constitution IV refactor audit: confirm `validate_rule_pack_paths` has exactly one caller (`_validate_profile_rule_packs`); confirm error-kind discrimination is centralized in `RulePackError`, not duplicated in the CLI envelope.

**Checkpoint**: US4 complete. FR-021 through FR-023 green. Fresh installs run without orphan paths; misconfigured installs fail loudly with distinct error kinds.

---

## Phase 7: User Story 5 — Users can navigate to any entity class by ID (Priority: P3)

**Goal**: Rewrite `auditgraph/query/node_view.py` with ID-prefix dispatch so `doc_*`, `chk_*`, `ent_*`, `commit_*`, `note_*` all resolve; unknown IDs return a structured not-found error.

**Independent Test**: Materialize document, chunk, entity, and git-provenance entity fixtures. Invoke `node_view` on each ID. Each resolves. Invoke with an unknown ID. Structured not-found returned.

### Tests for User Story 5 (write first, confirm failing)

- [X] T058 [P] [US5] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_node_lookup.py` with tests: `test_doc_id_resolves_to_document_view`, `test_chk_id_resolves_to_chunk_view`, `test_ent_id_resolves_to_entity_view`, `test_commit_id_resolves_via_entities_tree`, `test_unknown_id_returns_structured_not_found`, `test_unknown_doc_id_does_not_leak_oserror`, `test_fallthrough_finds_doc_id_misplaced_under_entities`.
- [X] T059 [US5] Run `pytest tests/test_spec028_node_lookup.py -v` and confirm ALL FAIL (the `doc_*` cases will fail with the current `FileNotFoundError` symptom from the Orpheus report).

### Implementation for User Story 5

- [X] T060 [US5] Rewrite `/home/socratesone/socratesone/auditgraph/auditgraph/query/node_view.py` exactly per `contracts/node-view-dispatch.md`. Keep the public `node_view(pkg_root, entity_id) -> dict` signature. Implement `_DISPATCH` table, `_resolve_document`, `_resolve_chunk`, `_resolve_entity` private helpers. Add the fall-through loop and the final structured not-found envelope.
- [X] T061 [US5] Confirm `/home/socratesone/socratesone/auditgraph/auditgraph/cli.py :: main` around line 446-450 still works with the new return shape. The existing handler already routes the dict through `_emit(payload)`, so no CLI change is expected — verify.
- [X] T062 [US5] Grep for other consumers: `grep -rn "from auditgraph.query.node_view\|from auditgraph.query import .*node_view\|node_view(" auditgraph/ llm-tooling/`. Confirm none break on the new error envelope.
- [X] T063 [US5] Run the US5 test file and confirm ALL PASS. Run full regression.
- [X] T064 [US5] Constitution IV refactor audit: confirm the `_DISPATCH` table is the sole source of prefix → resolver mapping; no per-type `if`/`elif` ladder survives anywhere.

**Checkpoint**: US5 complete. FR-024 through FR-026 green. `auditgraph node doc_*` works.

---

## Phase 8: User Story 6 — Run manifests carry truthful timestamps (Priority: P3)

**Goal**: Add `wall_clock_started_at` / `wall_clock_finished_at` fields to `StageManifest` and `IngestManifest`. Preserve the existing deterministic `started_at` / `finished_at`.

**Independent Test**: Run the pipeline. Inspect manifest. `wall_clock_*` fields reflect real time. `started_at` stays deterministic. `outputs_hash` unchanged across two runs.

### Tests for User Story 6 (write first, confirm failing)

- [X] T065 [P] [US6] Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_wall_clock_timestamps.py` with tests: `test_wall_clock_fields_present_in_stage_manifest`, `test_wall_clock_fields_present_in_ingest_manifest`, `test_wall_clock_now_returns_iso8601_within_seconds`, `test_deterministic_started_at_unchanged`, `test_outputs_hash_stable_across_runs_with_different_wall_clocks` (invariant I7), `test_wall_clock_monkeypatchable_in_tests`.
- [X] T066 [US6] Run `pytest tests/test_spec028_wall_clock_timestamps.py -v` and confirm ALL FAIL.

### Implementation for User Story 6

- [X] T067 [US6] Add `wall_clock_now()` helper to `/home/socratesone/socratesone/auditgraph/auditgraph/storage/hashing.py`, colocated with `deterministic_timestamp`. Implementation per `contracts/stage-manifest-warnings.md :: wall_clock_now()` section. Format: `"%Y-%m-%dT%H:%M:%SZ"`, UTC.
- [X] T068 [US6] Extend `StageManifest` and `IngestManifest` dataclasses in `/home/socratesone/socratesone/auditgraph/auditgraph/storage/manifests.py` with `wall_clock_started_at: str | None = None` and `wall_clock_finished_at: str | None = None`. Update `to_dict()` to emit the fields (always, so operators see them even on null).
- [X] T069 [US6] Update `_write_stage_manifest` in `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` to accept and thread the two new kwargs. Capture `wall_clock_now()` at stage entry (just after `_start = time.monotonic()`) and again at stage exit (just before constructing the manifest).
- [X] T070 [US6] Update `run_ingest`'s manifest construction at `/home/socratesone/socratesone/auditgraph/auditgraph/pipeline/runner.py` around line 267-278 to pass the wall-clock values to `build_manifest`. Update `build_manifest` in `/home/socratesone/socratesone/auditgraph/auditgraph/ingest/manifest.py` to accept and store them.
- [X] T071 [US6] Run the US6 test file and confirm ALL PASS. Run the full determinism regression suite and confirm `outputs_hash` fields are byte-identical across runs.
- [X] T072 [US6] Constitution IV refactor audit: confirm `wall_clock_now()` has exactly one production call site (inside `_write_stage_manifest` for stage manifests, and one call in `run_ingest` for the ingest manifest); confirm tests consistently use `monkeypatch.setattr` to pin time.

**Checkpoint**: US6 complete. FR-027 through FR-029 green. Manifests carry truthful timestamps without regressing determinism.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation, documentation sync, MCP tool registration, and end-to-end verification against `quickstart.md`.

- [X] T073 [P] Update `/home/socratesone/socratesone/auditgraph/llm-tooling/tool.manifest.json`: verify the `ag_list` and `ag_query` tools already accept arbitrary `type` filter values (per Spec-023 they should). If any hardcoded type whitelist exists in the manifest, add `ag:section`, `ag:technology`, `ag:reference`. Update any examples to show one new type. Run `python llm-tooling/generate_skill_doc.py && python llm-tooling/generate_adapters.py` to regenerate derived artifacts.
- [X] T074 [P] Run `pytest /home/socratesone/socratesone/auditgraph/llm-tooling/tests -q` and confirm the MCP contract tests stay green (timeout limits, example presence, read-only designation).
- [X] T075 [P] Update `/home/socratesone/socratesone/auditgraph/CLAUDE.md`: flip the "Markdown sub-entity extraction (ag:section, ag:technology, ag:reference) is planned but not enabled" sentence to reflect shipped state. Add a Common Pitfalls entry documenting the `parse_status` / `source_origin` orthogonality and noting Spec-028 FR-001 as its source.
- [X] T076 [P] Update `/home/socratesone/socratesone/auditgraph/README.md` CLI Reference with any new flags or behavior. Update `/home/socratesone/socratesone/auditgraph/QUICKSTART.md` (if present) with a 3-line note that markdown corpora now produce structured sub-entities out of the box.
- [X] T077 [P] Append an entry to `/home/socratesone/socratesone/auditgraph/CHANGELOG.md` under `## Unreleased` summarizing Spec-028: bug fixes (BUG-1/2/4/5 + BUG-3 polish), new entity types, new warnings, new config stubs. Cite spec and plan paths.
- [X] T078 Write `/home/socratesone/socratesone/auditgraph/tests/test_spec028_end_to_end.py` executing a scripted version of `quickstart.md` §1-§10 against a tmp_path workspace. Marked `pytest.mark.slow` per the `[tool.pytest.ini_options] markers` convention. Asserts the acceptance checklist from quickstart.md mechanically, including the exact counts (4 sections / 5 technologies / 4 references), pruning behavior (§9), and cooccurrence exclusion (§10).
- [X] T078a [P] Write a reviewer acceptance checklist at `/home/socratesone/socratesone/auditgraph/specs/028-markdown-extraction/checklists/reviewer.md` containing the guardrail items from adjustments.md §12: no contradictions between `spec.md`, `data-model.md`, `research.md`, `contracts/`, `tasks.md`, and `quickstart.md`; quickstart can be executed mechanically end-to-end; every new entity/link shape has exactly one authoritative schema in data-model.md; every query/navigation claim maps to an existing command or an explicit task that modifies one; stale-entity behavior (pruning) is covered by at least one test. This file is consulted by the reviewer during `/speckit.analyze` at the close of implementation.
- [X] T079 Run `pytest tests/test_spec028_*.py -v` and confirm ALL Spec-028 tests pass (161+ new tests across 12+ files per plan.md Phase 1 structure).
- [X] T080 Run `pytest tests/ -v 2>&1 | tail -80` end-to-end. Confirm no regressions except the two pre-existing known failures documented in `CLAUDE.md` (NER model unavailable, Spec-011 redaction). If count matches pre-028 baseline, all new tests add to the green count.
- [X] T081 Execute `quickstart.md` manually against a scratch directory. Check every box in the "Acceptance checklist" at the bottom. Report any step that behaves unexpectedly as a defect to fix before merge.
- [X] T082 Run `ruff check /home/socratesone/socratesone/auditgraph` and confirm zero new lint findings.
- [X] T083 Final Constitution V audit: grep for any new code that imports `datetime` for hashable fields (must be zero); confirm `wall_clock_now()` is the only wall-clock entry point in production code; confirm no new config knobs beyond the one `extraction.markdown.enabled` flag.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies.
- **Phase 2 (Foundational)** → nothing beyond Phase 1 (foundational tasks are captured inside each user story to keep stories vertical).
- **Phase 3 (US1)** → Phase 1 complete.
- **Phase 4 (US2)** → Phase 1 complete. US2 is testable without US1 (acceptance scenarios cover first-run behavior). But the MERGE ORDER is US1 first because both touch `pipeline/runner.py :: run_extract`.
- **Phase 5 (US3)** → Phase 1 + 4 complete (the warning emitter reads the same entity list that US2 builds; testing US3 without US2 leaves the "1 entity from nonzero input" test path weak).
- **Phase 6 (US4)** → Phase 1 complete. Independent; can merge in parallel with any other story if the developer rebases.
- **Phase 7 (US5)** → Phase 1 complete. Fully independent of every other story.
- **Phase 8 (US6)** → Phase 1 + 5 complete (both US3 and US6 extend `StageManifest`; serialize the dataclass changes to avoid merge conflicts).
- **Phase 9 (Polish)** → all user stories complete.

### User Story Dependencies

| Story | Depends on (code) | Depends on (merge order) | Independently testable |
|-------|-------------------|--------------------------|------------------------|
| US1   | none              | after Phase 1            | yes                    |
| US2   | none              | after US1 (runner.py overlap) | yes (first-run only) |
| US3   | none strict; US2 recommended | after US2 (manifest overlap) | yes |
| US4   | none              | anywhere after Phase 1   | yes                    |
| US5   | none              | anywhere after Phase 1   | yes                    |
| US6   | none              | after US3 (manifest overlap) | yes                |

### Within Each User Story

- Fixtures [P] can be written in parallel (different files).
- Test files [P] can be written in parallel (different test files).
- Tests MUST fail before any implementation task in the same phase starts (Constitution III Red-Green-Refactor).
- Implementation tasks within a story are mostly sequential because they touch shared producer files (`runner.py`, `storage/manifests.py`).
- Final "run full regression" + "Constitution IV refactor audit" tasks close every story phase.

### Parallel Opportunities

- **Within US1**: T004, T005, T006 in parallel (three different test files).
- **Within US2**: T018, T019, T020, T021 in parallel (four different fixture files); T022, T023, T024, T025, T026 in parallel (five different test files).
- **Within US3**: only T037 marked [P] (single test file); implementation tasks sequential on shared files.
- **Within US4**: T047, T048 in parallel (two test files); T050, T051 in parallel (two stub YAMLs, different paths).
- **Within US5**: T058 only (single test file).
- **Within US6**: T065 only (single test file).
- **Within Polish**: T073–T077 all parallel (different files / different generators).

### Cross-story parallelism (with a team)

- Developer A: US1 + US3 + US6 (shared `runner.py` + `manifests.py` surface, sequence them).
- Developer B: US2 (largest story; touches `runner.py` but after US1 lands).
- Developer C: US4 + US5 (fully independent of the runner and manifest surface).

---

## Parallel Example: User Story 2

```bash
# T018-T021: fixtures can be created concurrently (different files, no interdependencies)
Task: "Create nested_headings.md fixture in tests/fixtures/spec028/"
Task: "Create code_and_links.md fixture in tests/fixtures/spec028/"
Task: "Create with_secrets.md fixture in tests/fixtures/spec028/"
Task: "Create workspace/ fixture with cross-linked markdown files"

# T022-T026: test files can be written concurrently after fixtures exist
Task: "Write test_spec028_markdown_sections.py"
Task: "Write test_spec028_markdown_technologies.py"
Task: "Write test_spec028_markdown_references.py"
Task: "Write test_spec028_markdown_determinism.py"
Task: "Write test_spec028_redaction_in_subentities.py"

# After T027 confirms failures, T028-T033 MUST be sequential (shared runner.py)
```

---

## Implementation Strategy

### MVP (P1 pair): ship US1 + US2 as the first deliverable

1. Complete Phase 1 (Setup): T001-T003. Takes ~5 minutes.
2. Complete Phase 3 (US1): T004-T017. Takes ~0.5 day for one developer.
3. **STOP & VALIDATE**: run `auditgraph run` twice on a markdown corpus; entities persist across runs.
4. Complete Phase 4 (US2): T018-T036. Takes ~1–1.5 days for one developer.
5. **STOP & VALIDATE**: run `auditgraph list --type ag:section`, `--type ag:technology`, `--type ag:reference`; counts match quickstart §2 expectations.
6. **MVP shippable**: SC-001, SC-002, SC-003, SC-004, SC-010, SC-011 all green.

### Incremental delivery of remaining stories

- US3 (honest status): ~0.25 day. Ship alone or batched with US4.
- US4 (honest config): ~0.25 day. Ship alone.
- US5 (node lookup): ~0.25 day. Ship alone or batched with US6.
- US6 (wall-clock): ~0.25 day. Ship after US3.
- Polish (Phase 9): ~0.5 day. Ship after all stories.

Total estimate for a single developer: ~3.5–4 days, not including review cycles.

### Parallel team strategy

With three developers:

- Days 1–2: All on Phase 1 + US1 + US2 (pair on US2 — it's the largest).
- Day 3 morning: Devs split — A on US3, B on US4, C on US5.
- Day 3 afternoon: Dev A picks up US6 (sequenced after US3 merges); B and C start Polish tasks.
- Day 4: Polish, quickstart walkthrough, final regression, merge.

---

## Notes

- **[P] tasks**: different files, no dependencies — safe to execute concurrently.
- **Story labels** map every implementation task to its user story for traceability against spec.md acceptance scenarios and success criteria.
- **TDD is mandatory** per Constitution III. Every phase's first implementation task is preceded by a "confirm FAIL" gate. Never skip the red step.
- **Commit after each task or logical group**. Never batch six tasks into one commit — Constitution IV requires vertical commits.
- **Stop at any checkpoint** to demo or deploy; each story delivers independent value.
- **Avoid**: same-file conflicts across [P] tasks, vague task descriptions without file paths, cross-story dependencies that break the "US can ship alone" contract.
- **Fixture hygiene**: new fixtures live under `tests/fixtures/spec028/`. Mirror the sharded layout established by Spec-023 and Spec-027 tests whenever entity/link records are involved.
- **Pre-existing failures**: two tests in the current suite are expected to fail (spaCy model missing, Spec-011 redaction). Do NOT conflate these with Spec-028 regressions. Compare against the pre-028 baseline count.
