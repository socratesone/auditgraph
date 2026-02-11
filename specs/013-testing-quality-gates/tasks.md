---

description: "Task list for implementing Testing and Quality Gates"

---

# Tasks: Testing and Quality Gates

**Input**: Design documents from `/specs/013-testing-quality-gates/`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create baseline fixture workspace under tests/fixtures/spec013/
- [X] T002 [P] Add golden artifact directory structure under tests/fixtures/spec013/golden/

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T003 [P] Add test matrix definition file in tests/fixtures/spec013/test-matrix.json
- [X] T004 [P] Add determinism fixture config in tests/fixtures/spec013/determinism/config.yaml
- [X] T005 [P] Add performance baseline config in tests/fixtures/spec013/performance/config.yaml

**Checkpoint**: Foundation ready (fixtures and configs available)

---

## Phase 3: User Story 1 - Verify coverage per pipeline stage (Priority: P1) 🎯 MVP

**Goal**: Stage-based test matrix is enforced with required unit and integration coverage.

**Independent Test**: Run tests/test_spec013_quality_gates.py and see missing coverage failures.

### Tests for User Story 1 (TDD)

- [X] T006 [P] [US1] Add matrix validation unit tests in tests/test_spec013_quality_gates.py
- [X] T007 [P] [US1] Add missing-stage coverage integration test in tests/test_spec013_quality_gates.py

### Implementation for User Story 1

- [X] T008 [US1] Implement matrix loader + validator in auditgraph/utils/quality_gates.py
- [X] T009 [US1] Implement quality gate runner with coverage checks in auditgraph/utils/quality_gates.py

**Checkpoint**: US1 passes and is independently testable.

---

## Phase 4: User Story 2 - Determinism regression gates (Priority: P2)

**Goal**: Determinism fixture comparisons block builds on byte mismatches or unstable ordering.

**Independent Test**: Run tests/test_spec013_determinism.py and observe byte-for-byte checks.

### Tests for User Story 2 (TDD)

- [X] T010 [P] [US2] Add determinism byte-compare tests in tests/test_spec013_determinism.py
- [X] T011 [P] [US2] Add stable ordering regression test in tests/test_spec013_determinism.py

### Implementation for User Story 2

- [X] T012 [US2] Implement determinism checker in auditgraph/utils/quality_gates.py
- [X] T013 [US2] Add fixture runner that produces artifacts under tests/fixtures/spec013/runs/ in auditgraph/utils/quality_gates.py

**Checkpoint**: US2 passes and is independently testable.

---

## Phase 5: User Story 3 - Performance and quality gates (Priority: P3)

**Goal**: Performance gates enforce NFR-2 thresholds with explicit failure reports.

**Independent Test**: Run tests/test_spec013_performance.py and verify failures when thresholds are exceeded by >10%.

### Tests for User Story 3 (TDD)

- [X] T014 [P] [US3] Add performance gate unit tests in tests/test_spec013_performance.py
- [X] T015 [P] [US3] Add performance threshold failure test in tests/test_spec013_performance.py

### Implementation for User Story 3

- [X] T016 [US3] Implement performance gate evaluator in auditgraph/utils/quality_gates.py
- [X] T017 [US3] Include gate failure reporting with stage/threshold/observed in auditgraph/utils/quality_gates.py

**Checkpoint**: US3 passes and is independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 [P] Validate specs/013-testing-quality-gates/quickstart.md against real CLI behavior; update if mismatched
- [ ] T019 Run full test suite and fix regressions: `pytest -q`

---

## Dependencies & Execution Order

### Dependency Graph (User Story Completion Order)

1. Phase 1 (Setup)
2. Phase 2 (Foundational) — blocks all user stories
3. US1 (P1) — matrix coverage checks
4. US2 (P2) — determinism gates
5. US3 (P3) — performance gates
6. Polish

### Parallel Opportunities

- Phase 2: T003–T005 can run in parallel.
- US1: T006–T007 can run in parallel.
- US2: T010–T011 can run in parallel.
- US3: T014–T015 can run in parallel.

### Parallel Example: User Story 1

- Matrix validation unit tests: tests/test_spec013_quality_gates.py
- Missing-stage coverage test: tests/test_spec013_quality_gates.py

### Parallel Example: User Story 2

- Determinism byte-compare tests: tests/test_spec013_determinism.py
- Stable ordering regression test: tests/test_spec013_determinism.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Implement US1 matrix validation and coverage gate
3. Validate quality gate failures on missing coverage

### Incremental Delivery

1. Add US2 determinism gates and re-run tests
2. Add US3 performance gates and re-run tests
