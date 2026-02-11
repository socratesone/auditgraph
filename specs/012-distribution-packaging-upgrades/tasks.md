---

description: "Task list for implementing Distribution, Packaging, and Upgrades"

---

# Tasks: Distribution, Packaging, and Upgrades

**Input**: Design documents from `/specs/012-distribution-packaging-upgrades/`

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Add artifact schema version constant in auditgraph/storage/audit.py

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T002 [P] Add compatibility and budget error types in auditgraph/errors.py
- [ ] T003 Add `schema_version` to manifest models in auditgraph/storage/manifests.py
- [ ] T004 Add `schema_version` propagation when building/writing manifests in auditgraph/ingest/manifest.py and auditgraph/pipeline/runner.py
- [ ] T005 Add footprint budget defaults + parsing helpers in auditgraph/config.py
- [ ] T006 Add footprint budget defaults to config/pkg.yaml

**Checkpoint**: Foundation ready (schema versioning + budget config available)

---

## Phase 3: User Story 1 - Install and run on supported OS (Priority: P1) 🎯 MVP

**Goal**: Supported OS targets and packaging expectations are clearly documented.

**Independent Test**: Follow README + docs to install and run `auditgraph version` on Linux/macOS.

### Implementation for User Story 1

- [ ] T007 [US1] Document supported OS targets + install steps in README.md
- [ ] T008 [US1] Update docs/environment-setup.md with Python 3.10+ and supported OS guidance

**Checkpoint**: US1 documentation is complete and usable.

---

## Phase 4: User Story 2 - Upgrade without data loss (Priority: P2)

**Goal**: Compatibility checks prevent reuse of incompatible artifacts and instruct rebuilds.

**Independent Test**: Create a run with an old schema version, then run ingest and verify rebuild guidance without rewriting artifacts.

### Tests for User Story 2 (TDD)

- [ ] T009 [P] [US2] Add compatibility helper unit tests in tests/test_spec012_compatibility.py
- [ ] T010 [P] [US2] Add ingest compatibility integration test in tests/test_spec012_compatibility.py

### Implementation for User Story 2

- [ ] T011 [US2] Implement compatibility helper in auditgraph/utils/compatibility.py
- [ ] T012 [US2] Enforce compatibility check before ingest/rebuild in auditgraph/pipeline/runner.py
- [ ] T013 [US2] Update manifest-related tests for schema_version changes in tests/test_spec003_determinism_audit.py and tests/test_spec005_pipeline_stages.py

**Checkpoint**: US2 passes and is independently testable.

---

## Phase 5: User Story 3 - Enforce disk footprint budgets (Priority: P3)

**Goal**: Derived artifacts respect configured disk budgets with warning and blocking thresholds.

**Independent Test**: Configure a low budget and confirm warn/block behavior on ingest and export.

### Tests for User Story 3 (TDD)

- [ ] T014 [P] [US3] Add budget evaluation unit tests in tests/test_spec012_budget.py
- [ ] T015 [P] [US3] Add budget enforcement integration test in tests/test_spec012_budget.py

### Implementation for User Story 3

- [ ] T016 [US3] Implement footprint budget evaluator in auditgraph/utils/budget.py
- [ ] T017 [US3] Enforce budget checks before writing ingest artifacts in auditgraph/pipeline/runner.py
- [ ] T018 [US3] Enforce budget checks for exports in auditgraph/export/json.py
- [ ] T019 [US3] Include budget warning/block details in CLI output in auditgraph/cli.py

**Checkpoint**: US3 passes and is independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T020 [P] Validate specs/012-distribution-packaging-upgrades/quickstart.md against real CLI behavior; update if mismatched
- [ ] T021 Run full test suite and fix regressions: `pytest -q`

---

## Dependencies & Execution Order

### Dependency Graph (User Story Completion Order)

1. Phase 1 (Setup)
2. Phase 2 (Foundational) — blocks all user stories
3. US1 (P1) — documentation baseline
4. US2 (P2) — compatibility enforcement
5. US3 (P3) — budget enforcement
6. Polish

### Parallel Opportunities

- Phase 2: T002, T005, T006 can run in parallel.
- US2: T009–T010 can run in parallel.
- US3: T014–T015 can run in parallel.

### Parallel Example: User Story 2

- Compatibility helper tests: tests/test_spec012_compatibility.py
- Ingest compatibility integration test: tests/test_spec012_compatibility.py

### Parallel Example: User Story 3

- Budget evaluator unit tests: tests/test_spec012_budget.py
- Budget enforcement integration test: tests/test_spec012_budget.py

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 + Phase 2
2. Implement US1 documentation updates
3. Validate `auditgraph version` install guidance on Linux/macOS

### Incremental Delivery

1. Add US2 compatibility enforcement and re-run tests
2. Add US3 budget enforcement and re-run tests
