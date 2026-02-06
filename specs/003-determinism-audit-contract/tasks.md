---

description: "Task list for determinism and audit contract implementation"
---

# Tasks: Determinism and Audit Contract

**Input**: Design documents from `/specs/003-determinism-audit-contract/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US3)
- Each task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add determinism/audit scaffolding

- [X] T001 Add run metadata fields to config/pkg.yaml and document in docs/spec/03-determinism-audit-contract.md
- [X] T002 [P] Add audit contract constants in auditgraph/storage/audit.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core structures for run manifests, config snapshots, and replay logs

- [X] T003 Extend run manifest schema with config hash and pipeline version in auditgraph/storage/manifests.py
- [X] T004 Add config snapshot writer in auditgraph/storage/config_snapshot.py
- [X] T005 Update replay log writer to include inputs/outputs hashes in auditgraph/pipeline/runner.py

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 - Deterministic Outputs (Priority: P1) 🎯 MVP

**Goal**: Deterministic run IDs and byte-for-byte reproducible outputs

**Independent Test**: Run ingest twice and compare manifests and artifacts for byte equality.

- [X] T006 [US1] Implement deterministic run ID computation from input hashes in auditgraph/storage/hashing.py
- [X] T007 [US1] Use deterministic run ID and config hash in auditgraph/pipeline/runner.py
- [X] T008 [US1] Persist outputs hash in run manifest in auditgraph/storage/manifests.py

---

## Phase 4: User Story 2 - Auditable Provenance (Priority: P2)

**Goal**: Store provenance and audit artifacts for derived outputs

**Independent Test**: Inspect manifests and verify provenance entries exist for a run.

- [X] T009 [US2] Add provenance record schema in auditgraph/storage/provenance.py
- [X] T010 [US2] Record provenance for ingest sources in auditgraph/pipeline/runner.py
- [X] T011 [US2] Add provenance index writer in auditgraph/storage/provenance.py

---

## Phase 5: User Story 3 - Stable Ranking (Priority: P3)

**Goal**: Deterministic tie-break ordering for equal scores

**Independent Test**: Run the same query repeatedly and confirm stable order.

- [X] T012 [US3] Add stable tie-break ordering in auditgraph/query/ranking.py
- [X] T013 [US3] Record tie-break keys in query responses in auditgraph/query/keyword.py

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation alignment

- [X] T014 [P] Update README.md with determinism and audit contract notes
- [X] T015 [P] Update specs/003-determinism-audit-contract/quickstart.md with replay log example

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational
- **US2 (P2)**: Can start after Foundational; relies on manifest schema
- **US3 (P3)**: Can start after Foundational

### Parallel Opportunities

- T001 and T002 can run in parallel
- Phase 6 documentation tasks can run in parallel

---

## Parallel Example: User Story 1

- T006 Implement deterministic run ID computation in auditgraph/storage/hashing.py
- T007 Use deterministic run ID and config hash in auditgraph/pipeline/runner.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. Validate determinism via repeated ingest runs

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate determinism
3. Add US2 → validate provenance audit records
4. Add US3 → validate stable ranking
