---

description: "Task list for knowledge model implementation"
---

# Tasks: Knowledge Model

**Input**: Design documents from `/specs/004-knowledge-model/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US3)
- Each task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish knowledge model structures

- [X] T001 Add knowledge model config defaults in config/pkg.yaml and document in docs/spec/04-knowledge-model.md
- [X] T002 [P] Add canonical type constants in auditgraph/storage/knowledge_types.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures for entities and claims

- [X] T003 Add entity/claim schema definitions in auditgraph/storage/knowledge_models.py
- [X] T004 Add contradiction flags and validity window types in auditgraph/storage/knowledge_models.py
- [X] T005 Add namespace resolution helpers in auditgraph/storage/ontology.py

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 - Canonical Definitions (Priority: P1) 🎯 MVP

**Goal**: Canonical types for entities, claims, notes, tasks, decisions, events

**Independent Test**: Create sample records and confirm schema validation for each type.

- [X] T006 [US1] Implement canonical model validators in auditgraph/storage/knowledge_models.py
- [X] T007 [US1] Add canonical key normalization in auditgraph/storage/ontology.py
- [X] T008 [US1] Ensure ingest metadata maps to canonical types in auditgraph/ingest/sources.py

---

## Phase 4: User Story 2 - Contradictions & Time (Priority: P2)

**Goal**: Preserve contradictory claims and temporal facts

**Independent Test**: Store conflicting claims and verify both are retained with flags and validity windows.

- [X] T009 [US2] Add contradiction tagging helpers in auditgraph/storage/knowledge_models.py
- [X] T010 [US2] Add validity window support to claims in auditgraph/storage/knowledge_models.py

---

## Phase 5: User Story 3 - Confidence & Ontology (Priority: P3)

**Goal**: Rule-based confidence and namespace-aware types

**Independent Test**: Store rule-derived claims with confidence and verify namespaced types.

- [X] T011 [US3] Add rule-based confidence assignment in auditgraph/storage/knowledge_models.py
- [X] T012 [US3] Enforce namespace prefix on entity types in auditgraph/storage/ontology.py

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation alignment

- [X] T013 [P] Update README.md with knowledge model summary
- [X] T014 [P] Update specs/004-knowledge-model/quickstart.md with example canonical types

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational
- **US2 (P2)**: Can start after Foundational
- **US3 (P3)**: Can start after Foundational

### Parallel Opportunities

- T001 and T002 can run in parallel
- Documentation tasks in Phase 6 can run in parallel

---

## Parallel Example: User Story 1

- T006 Implement canonical model validators in auditgraph/storage/knowledge_models.py
- T007 Add canonical key normalization in auditgraph/storage/ontology.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. Validate canonical models with sample data

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate canonical type mapping
3. Add US2 → validate contradictions + temporal facts
4. Add US3 → validate confidence + namespaces
