# Tasks: PDF and DOC Ingestion

**Input**: Design documents from `/specs/017-pdf-doc-ingestion/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/document-ingestion-contract.yaml`, `quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare dependencies, fixtures, and config surfaces required by all user stories.

- [X] T001 Add PDF/DOCX extractor dependencies to requirements in requirements-dev.txt
- [X] T057 Add runtime/package dependency declarations for `pypdf` and `python-docx` in pyproject.toml
- [X] T058 Add dependency consistency check between pyproject.toml and requirements-dev.txt in tests/test_spec017_foundation.py
- [X] T002 Add/verify ingestion config keys for OCR policy and token chunking in config/pkg.yaml
- [X] T003 Add concrete fixture assets `sample.pdf`, `scanned.pdf`, `sample.docx` under tests/fixtures/documents/
- [X] T004 Add fixture loading helpers for spec017 tests in tests/support.py
- [X] T048 Add deterministic fixture-generation script and fixture manifest checksums in tests/fixtures/documents/generate_fixtures.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared extraction/chunking/provenance scaffolding required before story work.

**⚠️ CRITICAL**: No user story implementation starts before this phase completes.

- [X] T049 [P] Add failing foundational parser-routing contract tests in tests/test_spec017_foundation.py
- [X] T050 [P] Add failing foundational config-hash and status-shape tests in tests/test_spec017_foundation.py
- [X] T051 [P] Add failing foundational normalization/chunk helper contract tests in tests/test_spec017_foundation.py
- [X] T005 Define document extraction result and segment/chunk types in auditgraph/extract/document_types.py
- [X] T006 [P] Implement deterministic text normalization helpers in auditgraph/utils/document_text.py
- [X] T007 [P] Implement token-based chunking helper with overlap in auditgraph/utils/chunking.py
- [X] T008 Implement extractor backend selection and routing hooks in auditgraph/ingest/parsers.py
- [X] T009 Implement ingestion config hash helper for document runs in auditgraph/storage/config_snapshot.py
- [X] T010 Implement per-file status reason plumbing for ok/skipped/failed in auditgraph/ingest/importer.py
- [X] T011 Wire importer status reporting into CLI ingest output in auditgraph/cli.py

**Checkpoint**: Foundation ready for independent user story delivery.

---

## Phase 3: User Story 1 - Ingest PDF and DOCX content (Priority: P1) 🎯 MVP

**Goal**: Ingest `.pdf` and `.docx` deterministically through existing import+ingest flow, skip unchanged files by hash, and reject `.doc` with explicit reasons.

**Independent Test**: Import+ingest mixed fixtures and verify deterministic artifacts plus explicit skip/failure reasons.

### Tests for User Story 1 (write first, must fail first)

- [X] T012 [P] [US1] Add parser selection and unsupported `.doc` behavior tests in tests/test_spec017_document_ingestion.py
- [X] T013 [P] [US1] Add deterministic normalization and chunk boundary tests in tests/test_spec017_document_ingestion.py
- [X] T014 [P] [US1] Add unchanged-hash skip reason tests in tests/test_spec017_document_ingestion.py
- [X] T015 [P] [US1] Add OCR default-off behavior tests for image-only fixtures in tests/test_spec017_document_ingestion.py
- [X] T052 [P] [US1] Add OCR `auto` mode behavior tests (text-layer fallback conditions) in tests/test_spec017_document_ingestion.py
- [X] T053 [P] [US1] Add OCR `on` mode behavior tests (forced OCR path) in tests/test_spec017_document_ingestion.py
- [X] T054 [P] [US1] Add overwrite-in-place regression tests with hash-history traceability in tests/test_spec017_document_ingestion.py

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement PDF text-layer backend extraction in auditgraph/extract/pdf_backend.py
- [X] T017 [P] [US1] Implement DOCX OOXML backend extraction in auditgraph/extract/docx_backend.py
- [X] T018 [US1] Register PDF/DOCX backends and block `.doc` in auditgraph/ingest/parsers.py
- [X] T019 [US1] Integrate backend extraction into import pipeline in auditgraph/ingest/importer.py
- [X] T020 [US1] Persist extracted document/segment/chunk artifacts in auditgraph/storage/artifacts.py
- [X] T021 [US1] Enforce deterministic IDs for document/segment/chunk records in auditgraph/storage/hashing.py
- [X] T022 [US1] Enforce OCR policy default-off and explicit opt-in handling in auditgraph/config.py
- [X] T023 [US1] Emit explicit per-file reasons for `.doc`, encrypted/corrupt, and oversized failures in auditgraph/ingest/manifest.py
- [X] T055 [US1] Implement OCR mode matrix handling (`off|auto|on`) in auditgraph/ingest/parsers.py and auditgraph/extract/pdf_backend.py
- [X] T056 [US1] Implement overwrite-in-place update flow and hash-history audit logging in auditgraph/ingest/importer.py and auditgraph/ingest/manifest.py

**Checkpoint**: US1 delivers day-1 ingestion MVP independently.

---

## Phase 4: User Story 2 - Retrieve with source provenance (Priority: P2)

**Goal**: Return queryable chunk results with metadata-only citations (`source_path` + location fields), no inline markers in chunk text.

**Independent Test**: Query ingested documents and verify citation metadata completeness and chunk text cleanliness.

### Tests for User Story 2 (write first, must fail first)

- [X] T024 [P] [US2] Add chunk citation metadata presence tests in tests/test_spec017_query_citations.py
- [X] T025 [P] [US2] Add no-inline-citation-marker tests in tests/test_spec017_query_citations.py
- [X] T026 [P] [US2] Add DOCX paragraph-order provenance tests in tests/test_spec017_query_citations.py

### Implementation for User Story 2

- [X] T027 [P] [US2] Add document chunk loading utilities in auditgraph/storage/loaders.py
- [X] T028 [US2] Extend keyword query pipeline to include chunk citation metadata in auditgraph/query/keyword.py
- [X] T029 [US2] Extend node/detail view responses to expose chunk provenance fields in auditgraph/query/node_view.py
- [X] T030 [US2] Ensure retrieval payloads remain metadata-only (no inline markers) in auditgraph/normalize/text.py
- [X] T031 [US2] Add deterministic ordering for chunk retrieval output in auditgraph/query/ranking.py

**Checkpoint**: US1 + US2 are independently testable and usable.

---

## Phase 5: User Story 3 - Preserve provenance in exports/sync (Priority: P3)

**Goal**: Keep document/chunk provenance intact across `export`, `export-neo4j`, and `sync-neo4j` outputs.

**Independent Test**: Ingest docs, run exports/sync, then assert provenance fields exist in exported/synced records.

### Tests for User Story 3 (write first, must fail first)

- [X] T032 [P] [US3] Add JSON export provenance retention tests in tests/test_spec017_export_sync_provenance.py
- [X] T033 [P] [US3] Add Neo4j Cypher export provenance retention tests in tests/test_spec017_export_sync_provenance.py
- [X] T034 [P] [US3] Add Neo4j sync provenance retention tests in tests/test_spec017_export_sync_provenance.py

### Implementation for User Story 3

- [X] T035 [P] [US3] Map document/chunk provenance fields in Neo4j record conversion in auditgraph/neo4j/records.py
- [X] T036 [US3] Ensure Cypher builder preserves provenance properties for document/chunk nodes in auditgraph/neo4j/cypher_builder.py
- [X] T037 [US3] Ensure Neo4j export path includes provenance-bearing records in auditgraph/neo4j/export.py
- [X] T038 [US3] Ensure Neo4j sync path writes provenance-bearing properties in auditgraph/neo4j/sync.py
- [X] T039 [US3] Ensure generic export JSON includes document/chunk provenance in auditgraph/export/json.py

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, docs, and full validation.

- [X] T040 [P] Update user-facing docs for PDF/DOCX support and OCR default-off in README.md
- [X] T041 [P] Update environment/setup docs for new extractor dependencies and config keys in docs/environment-setup.md
- [X] T042 [P] Update MCP guidance for document citation expectations in MCP_GUIDE.md
- [X] T043 Run focused test suite for spec017 coverage in tests/test_spec017_document_ingestion.py
- [X] T044 Run focused test suite for retrieval/export provenance in tests/test_spec017_query_citations.py
- [X] T045 Run focused test suite for export/sync provenance in tests/test_spec017_export_sync_provenance.py
- [ ] T046 Run full repository tests and resolve only regressions caused by this feature in tests/
- [ ] T047 Validate quickstart end-to-end commands in specs/017-pdf-doc-ingestion/quickstart.md
- [X] T059 Validate SC-001 determinism + unchanged-skip thresholds with repeat-run assertion script in tests/test_spec017_success_criteria.py
- [X] T060 Validate SC-002 citation metadata completeness (100%) in tests/test_spec017_success_criteria.py
- [X] T061 Validate SC-003 batch failure-isolation and machine-readable reasons in tests/test_spec017_success_criteria.py
- [X] T062 Validate SC-004 export + Neo4j sync provenance retention checks in tests/test_spec017_success_criteria.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: starts immediately.
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all story work. Foundational tests (`T049`-`T051`) must fail before foundational implementation (`T005`-`T011`).
- **Phase 3 (US1)**: depends on Phase 2.
- **Phase 4 (US2)**: depends on Phase 2 and US1 artifact persistence.
- **Phase 5 (US3)**: depends on Phase 2 and US1 ingestion artifacts.
- **Phase 6 (Polish)**: depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: no dependency on other stories; defines MVP.
- **US2 (P2)**: depends on US1 document/chunk artifacts existing.
- **US3 (P3)**: depends on US1 artifacts; can proceed without US2.

### Within Each Story

- Tests must be authored first and fail before implementation.
- Backend/extractor work before pipeline wiring.
- Pipeline wiring before export/sync integration.
- Story completed and independently validated before moving on.

## Parallel Opportunities

- Setup parallel tasks: `T003`, `T004`, `T048`, `T057`, `T058`.
- Foundational parallel tests: `T049`-`T051`; foundational implementation: `T006`, `T007`.
- US1 parallel tests: `T012`-`T015`, `T052`-`T054`; parallel backend work: `T016`, `T017`.
- US2 parallel tests: `T024`–`T026`; parallel loader/query prep: `T027`, `T031`.
- US3 parallel tests: `T032`–`T034`; parallel mapping work: `T035`, `T039`.
- Polish parallel docs: `T040`, `T041`, `T042`.

## Parallel Example: User Story 1

```bash
# Write failing tests in parallel
Task: T012 [US1] tests/test_spec017_document_ingestion.py
Task: T013 [US1] tests/test_spec017_document_ingestion.py
Task: T014 [US1] tests/test_spec017_document_ingestion.py
Task: T015 [US1] tests/test_spec017_document_ingestion.py
Task: T052 [US1] tests/test_spec017_document_ingestion.py
Task: T053 [US1] tests/test_spec017_document_ingestion.py
Task: T054 [US1] tests/test_spec017_document_ingestion.py

# Implement independent extractors in parallel
Task: T016 [US1] auditgraph/extract/pdf_backend.py
Task: T017 [US1] auditgraph/extract/docx_backend.py
```

## Parallel Example: User Story 3

```bash
# Provenance retention tests in parallel
Task: T032 [US3] tests/test_spec017_export_sync_provenance.py
Task: T033 [US3] tests/test_spec017_export_sync_provenance.py
Task: T034 [US3] tests/test_spec017_export_sync_provenance.py

# Export mapping work in parallel
Task: T035 [US3] auditgraph/neo4j/records.py
Task: T039 [US3] auditgraph/export/json.py
```

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate deterministic PDF/DOCX ingest and skip/failure behavior.
4. Demo MVP before expanding to retrieval/export work.

### Incremental Delivery

1. Ship US1 (core ingestion).
2. Add US2 (query-time citations).
3. Add US3 (export/sync provenance retention).
4. Finish with Phase 6 polish and SC validation tasks (`T059`-`T062`).

### Team Parallel Strategy

1. One developer completes foundational pipeline scaffolding.
2. Then split by story:
   - Dev A: US1 ingest backends + pipeline wiring.
   - Dev B: US2 retrieval/citation outputs.
   - Dev C: US3 export/sync provenance mapping.
3. Rejoin for integration tests and docs.
