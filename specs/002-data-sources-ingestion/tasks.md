---

description: "Task list for data sources and ingestion policy implementation"
---

# Tasks: Data Sources and Ingestion Policy

**Input**: Design documents from `/specs/002-data-sources-ingestion/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US3)
- Each task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare configuration and ingestion policy scaffolding

- [ ] T001 Add ingestion policy defaults and documentation in config/pkg.yaml and docs/spec/02-data-sources-ingestion.md
- [ ] T002 [P] Add ingestion policy constants and helpers in auditgraph/ingest/policy.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures for tracking ingest status and skip reasons

- [ ] T003 Extend ingest record schema to include skip reason in auditgraph/storage/manifests.py
- [ ] T004 Update artifact writer to persist skip reason fields in auditgraph/storage/artifacts.py
- [ ] T005 Update ingest manifest writer to include skipped file counts in auditgraph/ingest/manifest.py

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 - Day-1 Sources Definition (Priority: P1) 🎯 MVP

**Goal**: Enforce day-1 allowlist and record unsupported sources with reasons

**Independent Test**: Run `auditgraph ingest` on a mixed workspace and confirm only allowed formats are ingested and unsupported files are reported as skipped.

- [ ] T006 [US1] Implement allowlist and parser selection in auditgraph/ingest/parsers.py
- [ ] T007 [US1] Implement skip reason mapping for unsupported formats in auditgraph/ingest/parsers.py
- [ ] T008 [US1] Enforce allowlist in scanner pipeline in auditgraph/ingest/scanner.py
- [ ] T009 [US1] Persist skipped file records with reasons in auditgraph/ingest/sources.py

---

## Phase 4: User Story 2 - Capture Channels (Priority: P2)

**Goal**: Support manual import and directory scan ingestion controls

**Independent Test**: Run directory scan and manual import commands on the same workspace and confirm deterministic file lists.

- [ ] T010 [US2] Add manual import CLI command in auditgraph/cli.py
- [ ] T011 [US2] Implement manual import handler in auditgraph/ingest/importer.py
- [ ] T012 [US2] Integrate manual import into pipeline runner in auditgraph/pipeline/runner.py

---

## Phase 5: User Story 3 - Normalization Rules (Priority: P3)

**Goal**: Normalize Markdown frontmatter to canonical schema

**Independent Test**: Ingest Markdown notes with and without frontmatter and verify normalized fields (title, tags, project, status).

- [ ] T013 [US3] Implement frontmatter parser and schema normalization in auditgraph/ingest/frontmatter.py
- [ ] T014 [US3] Wire frontmatter normalization into Markdown parsing in auditgraph/ingest/parsers.py
- [ ] T015 [US3] Add normalized metadata to source records in auditgraph/ingest/sources.py

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and config alignment

- [ ] T016 [P] Update README.md with day-1 ingestion scope and limitations
- [ ] T017 [P] Update specs/002-data-sources-ingestion/quickstart.md with manual import examples

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational
- **US2 (P2)**: Can start after Foundational; leverages scanning utilities from US1
- **US3 (P3)**: Can start after Foundational; builds on Markdown parsing from US1

### Parallel Opportunities

- T001 and T002 can run in parallel
- Documentation tasks in Phase 6 can run in parallel

---

## Parallel Example: User Story 1

- T006 Implement allowlist and parser selection in auditgraph/ingest/parsers.py
- T008 Enforce allowlist in scanner pipeline in auditgraph/ingest/scanner.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. Validate US1 independently via `auditgraph ingest`

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate day-1 allowlist and skipped file reporting
3. Add US2 → validate manual import and directory scan control
4. Add US3 → validate canonical frontmatter normalization
