---
description: "Task list for Automation and Jobs"
---

# Tasks: Automation and Jobs

**Input**: Design documents from `/specs/010-automation-jobs/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/automation-jobs.openapi.yaml, quickstart.md
**Tests**: Required (TDD per plan.md)
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create baseline jobs config in config/jobs.yaml with one example job and comments
- [x] T002 [P] Add test fixtures for jobs config in tests/fixtures/jobs/ (valid.yaml, invalid.yaml, duplicate.yaml)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T003 Add shared job error types and helpers in auditgraph/errors.py
- [x] T004 [P] Add YAML loader + config file discovery in auditgraph/jobs/config.py
- [x] T005 [P] Add output path resolver stub and JobRun record container in auditgraph/jobs/reports.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run Jobs Manually (Priority: P1) 🎯 MVP

**Goal**: Run a named job manually and record status + output path

**Independent Test**: Run a job by name and verify output artifact + status record; unknown job returns structured error and non-zero exit

### Tests for User Story 1 (TDD)

- [x] T006 [P] [US1] Add failing test for manual job run success in tests/test_user_story_jobs_run.py
- [x] T007 [P] [US1] Add failing test for unknown job error and exit code in tests/test_user_story_jobs_run.py
- [x] T008 [P] [US1] Add failing contract test for JobsRunResponse and ErrorResponse in tests/test_spec010_automation_jobs_contract.py

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement `jobs run` CLI command and response formatting in auditgraph/cli.py
- [x] T010 [US1] Implement job action dispatch for report.changed_since in auditgraph/jobs/runner.py
- [x] T011 [US1] Record JobRun status/output in auditgraph/jobs/reports.py
- [x] T012 [US1] Wire structured errors to non-zero exit codes for `jobs run` in auditgraph/cli.py
- [x] T013 [US1] Ensure output writing for manual runs uses resolved path in auditgraph/jobs/runner.py

**Checkpoint**: User Story 1 fully functional and independently testable

---

## Phase 4: User Story 2 - Job Configuration Schema (Priority: P2)

**Goal**: Define a consistent schema, validate config, and list configured jobs

**Independent Test**: Parse config and list jobs; invalid config yields structured error

### Tests for User Story 2 (TDD)

- [x] T014 [P] [US2] Add failing test for `jobs list` output in tests/test_user_story_jobs_list.py
- [x] T015 [P] [US2] Add failing test for invalid config error in tests/test_user_story_jobs_list.py
- [x] T016 [P] [US2] Add failing contract test for JobsListResponse and ErrorResponse in tests/test_spec010_automation_jobs_contract.py

### Implementation for User Story 2

- [x] T017 [P] [US2] Implement JobConfig schema + validation rules in auditgraph/jobs/config.py
- [x] T018 [P] [US2] Add duplicate job name detection in auditgraph/jobs/config.py
- [x] T019 [US2] Implement `jobs list` CLI command in auditgraph/cli.py
- [x] T020 [US2] Map config validation errors to structured CLI responses in auditgraph/cli.py
- [x] T021 [US2] Ensure missing config file yields structured error in auditgraph/jobs/config.py

**Checkpoint**: User Story 2 fully functional and independently testable

---

## Phase 5: User Story 3 - Job Outputs and Storage (Priority: P3)

**Goal**: Provide deterministic output locations for job artifacts

**Independent Test**: Run a job and confirm output path matches the documented rules

### Tests for User Story 3 (TDD)

- [x] T022 [P] [US3] Add failing test for default output path rule in tests/test_user_story_job_outputs.py
- [x] T023 [P] [US3] Add failing test for output path override in tests/test_user_story_job_outputs.py

### Implementation for User Story 3

- [x] T024 [P] [US3] Implement default output path resolution in auditgraph/jobs/reports.py
- [x] T025 [US3] Apply output path override logic in auditgraph/jobs/config.py
- [x] T026 [US3] Ensure JobRun records output path on success/failure in auditgraph/jobs/runner.py

**Checkpoint**: User Story 3 fully functional and independently testable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T027 [P] Update README.md with jobs config location and CLI usage
- [x] T028 [P] Update docs/environment-setup.md with config/jobs.yaml and jobs commands
- [x] T029 [P] Validate specs/010-automation-jobs/quickstart.md steps against CLI behavior
- [x] T030 Run full pytest suite in tests/ and fix any regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only
- **User Story 2 (P2)**: Depends on Foundational only
- **User Story 3 (P3)**: Depends on Foundational only

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Validation/models before services
- Services before CLI wiring
- Output handling before recording run status

---

## Parallel Execution Examples

### User Story 1

Task: "Add failing test for manual job run success in tests/test_user_story_jobs_run.py"
Task: "Add failing test for unknown job error and exit code in tests/test_user_story_jobs_run.py"
Task: "Add failing contract test for JobsRunResponse and ErrorResponse in tests/test_spec010_automation_jobs_contract.py"

### User Story 2

Task: "Add failing test for `jobs list` output in tests/test_user_story_jobs_list.py"
Task: "Add failing test for invalid config error in tests/test_user_story_jobs_list.py"
Task: "Add failing contract test for JobsListResponse and ErrorResponse in tests/test_spec010_automation_jobs_contract.py"

### User Story 3

Task: "Add failing test for default output path rule in tests/test_user_story_job_outputs.py"
Task: "Add failing test for output path override in tests/test_user_story_job_outputs.py"

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate User Story 1 independently (tests and CLI behavior)

### Incremental Delivery

1. Setup + Foundational complete
2. Implement User Story 1 → test → demo
3. Implement User Story 2 → test → demo
4. Implement User Story 3 → test → demo
5. Finish polish tasks and run full test suite
