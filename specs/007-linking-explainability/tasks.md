---

description: "Task list for Linking and Explainability"
---

# Tasks: Linking and Explainability

**Input**: Design documents from `/specs/007-linking-explainability/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize feature documentation scaffolding

- [ ] T001 Create specs/007-linking-explainability/spec.md from template and set feature metadata
- [ ] T002 [P] Create specs/007-linking-explainability/plan.md from template with technical context

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared linking terminology and research context used by all stories

- [ ] T003 Define baseline link policy and terminology in docs/spec/07-linking-explainability.md
- [ ] T004 [P] Document key design decisions in specs/007-linking-explainability/research.md

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 - Deterministic Link Rules (Priority: P1) 🎯 MVP

**Goal**: Document deterministic link rules, supported link types, and required metadata.

**Independent Test**: Review docs/spec/07-linking-explainability.md to confirm link policy, types, and metadata requirements.

### Implementation for User Story 1

- [ ] T005 [US1] Document link generation policy and supported types in docs/spec/07-linking-explainability.md
- [ ] T006 [P] [US1] Define Link Rule and Link Artifact entities in specs/007-linking-explainability/data-model.md
- [ ] T007 [US1] Update specs/007-linking-explainability/spec.md with a link policy summary section

**Checkpoint**: User Story 1 link rules are documented and reviewable

---

## Phase 4: User Story 2 - Explainability Payloads (Priority: P2)

**Goal**: Define explainability payload requirements for link artifacts.

**Independent Test**: Validate each link artifact includes rule id, evidence references, and scores when applicable.

### Implementation for User Story 2

- [ ] T008 [US2] Document explainability payload fields in docs/spec/07-linking-explainability.md
- [ ] T009 [P] [US2] Define explainability payload schema in specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml
- [ ] T010 [P] [US2] Add explainability validation rules in specs/007-linking-explainability/data-model.md

**Checkpoint**: Explainability payload requirements are captured in docs and contract

---

## Phase 5: User Story 3 - Backlinks Policy (Priority: P3)

**Goal**: Document backlinks strategy and deterministic ordering rules.

**Independent Test**: Verify backlinks policy and ordering rules are documented and deterministic.

### Implementation for User Story 3

- [ ] T011 [US3] Document backlinks policy and ordering rules in docs/spec/07-linking-explainability.md
- [ ] T012 [P] [US3] Document backlinks policy and ordering in specs/007-linking-explainability/spec.md
- [ ] T013 [US3] Add backlinks policy entity and validation rules in specs/007-linking-explainability/data-model.md

**Checkpoint**: Backlinks policy is documented and consistent

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ensure documentation consistency and update onboarding references

- [ ] T014 [P] Update specs/007-linking-explainability/quickstart.md to reference final payloads and policy
- [ ] T015 [P] Update docs/clarifying-answers.md with linking policy decisions and defaults
- [ ] T016 Run a consistency pass for docs/spec/07-linking-explainability.md and specs/007-linking-explainability/spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: No dependencies after Foundational
- **US2 (P2)**: Can start after Foundational; references US1 link policy
- **US3 (P3)**: Can start after Foundational; references US1 link policy and US2 payload fields

### Parallel Opportunities

- T002 and T004 can run in parallel with T001/T003
- Within US1, T005 and T006 can run in parallel
- Within US2, T008, T009, and T010 can run in parallel
- Within US3, T011 and T012 can run in parallel (T013 depends on T012)
- Polish tasks T014–T015 can run in parallel after story completion

---

## Parallel Example: User Story 2

```bash
Task: "Document explainability payload fields in docs/spec/07-linking-explainability.md"
Task: "Define explainability payload schema in specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml"
Task: "Add explainability validation rules in specs/007-linking-explainability/data-model.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate User Story 1 independently via the link policy checklist

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate link policy completeness
3. Add US2 → validate explainability payload completeness
4. Add US3 → validate backlinks policy coverage

---

## Notes

- [P] tasks = different files, no dependencies
- Each user story is independently reviewable
- Ensure docs/spec/07-linking-explainability.md remains the canonical linking definition
- Update README.md only if onboarding or navigation changes
