---

description: "Task list for Storage Layout and Artifacts"
---

# Tasks: Storage Layout and Artifacts

**Input**: Design documents from `/specs/006-storage-layout-artifacts/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize feature documentation scaffolding

- [X] T001 Create specs/006-storage-layout-artifacts/spec.md from template and set feature metadata
- [X] T002 [P] Create specs/006-storage-layout-artifacts/plan.md from template with technical context

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared layout terminology and research context used by all stories

- [X] T003 Define canonical storage root and run folder naming in docs/spec/06-storage-layout-artifacts.md
- [X] T004 [P] Document key design decisions in specs/006-storage-layout-artifacts/research.md

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 - Directory Layout (Priority: P1) 🎯 MVP

**Goal**: Provide a deterministic directory layout for all artifact types.

**Independent Test**: Review docs/spec/06-storage-layout-artifacts.md to confirm each artifact type lists a canonical path and naming rule.

### Implementation for User Story 1

- [X] T005 [US1] Document directory structure for sources, entities, claims, links, indexes in docs/spec/06-storage-layout-artifacts.md
- [X] T006 [P] [US1] Define Artifact Root entity and relationships in specs/006-storage-layout-artifacts/data-model.md
- [X] T007 [US1] Update specs/006-storage-layout-artifacts/spec.md with a directory layout summary section

**Checkpoint**: User Story 1 layout is documented and reviewable

---

## Phase 4: User Story 2 - Artifact Schemas (Priority: P2)

**Goal**: Define required fields and versioning for artifact schemas.

**Independent Test**: Validate each artifact schema lists required fields and a version identifier.

### Implementation for User Story 2

- [X] T008 [US2] Document artifact schema fields and versioning rules in docs/spec/06-storage-layout-artifacts.md
- [X] T009 [P] [US2] Define artifact schemas in specs/006-storage-layout-artifacts/contracts/storage-artifacts.openapi.yaml
- [X] T010 [P] [US2] Add artifact schema validation rules in specs/006-storage-layout-artifacts/data-model.md

**Checkpoint**: Artifact schema requirements are captured in docs and contract

---

## Phase 5: User Story 3 - Sharding and Stable IDs (Priority: P3)

**Goal**: Document sharding rules and stable ID canonicalization.

**Independent Test**: Verify sharding rules and stable ID steps are documented and deterministic.

### Implementation for User Story 3

- [X] T011 [US3] Document sharding rules and prefix length in docs/spec/06-storage-layout-artifacts.md
- [X] T012 [P] [US3] Document stable ID canonicalization inputs and hashing rules in specs/006-storage-layout-artifacts/spec.md
- [X] T013 [US3] Add stable ID and sharding validation rules in specs/006-storage-layout-artifacts/data-model.md

**Checkpoint**: Sharding and stable ID rules are documented and consistent

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ensure documentation consistency and update onboarding references

- [X] T014 [P] Update specs/006-storage-layout-artifacts/quickstart.md to reference final schemas and sharding rules
- [X] T015 [P] Update docs/clarifying-answers.md with storage layout decisions and defaults
- [X] T016 Run a consistency pass for docs/spec/06-storage-layout-artifacts.md and specs/006-storage-layout-artifacts/spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: No dependencies after Foundational
- **US2 (P2)**: Can start after Foundational; references US1 directory layout
- **US3 (P3)**: Can start after Foundational; references US1 layout and US2 schemas

### Parallel Opportunities

- T002 and T004 can run in parallel with T001/T003
- Within US1, T005 and T006 can run in parallel
- Within US2, T008, T009, and T010 can run in parallel
- Within US3, T011 and T012 can run in parallel (T013 depends on T012 for canonicalization details)
- Polish tasks T014–T015 can run in parallel after story completion

---

## Parallel Example: User Story 2

```bash
Task: "Document artifact schema fields and versioning rules in docs/spec/06-storage-layout-artifacts.md"
Task: "Define artifact schemas in specs/006-storage-layout-artifacts/contracts/storage-artifacts.openapi.yaml"
Task: "Add artifact schema validation rules in specs/006-storage-layout-artifacts/data-model.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate User Story 1 independently via the layout checklist

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate directory layout completeness
3. Add US2 → validate schema completeness
4. Add US3 → validate sharding and stable ID coverage

---

## Notes

- [P] tasks = different files, no dependencies
- Each user story is independently reviewable
- Ensure docs/spec/06-storage-layout-artifacts.md remains the canonical storage definition
- Update README.md only if onboarding or navigation changes
