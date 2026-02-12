---

description: "Task list for implementing MCP Tools and LLM Integration"

---

# Tasks: MCP Tools and LLM Integration

**Input**: Design documents from `/specs/016-mcp-tools-llm-integration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD is required by the project constitution and spec. All user story tests must be written and fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create llm-tooling/ directory structure with mcp/, adapters/, tests/, and placeholder files in llm-tooling/README.md and llm-tooling/.gitkeep
- [x] T002 [P] Document read-only rules, error model, and regeneration steps in llm-tooling/README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Define CLI tool inventory constants (read/write) in auditgraph/utils/mcp_inventory.py
- [x] T004 [P] Define normalized error codes and helper in auditgraph/utils/mcp_errors.py
- [x] T005 [P] Add shared test fixtures for manifest loading and environment setup in llm-tooling/tests/conftest.py

**Checkpoint**: Foundation ready (shared inventory, error model, and test scaffolding)

---

## Phase 3: User Story 1 - Interface-neutral tool manifest (Priority: P1) MVP

**Goal**: Tool manifest defines all CLI-mapped tools with strict schemas and examples.

**Independent Test**: Validate tool.manifest.json includes every CLI command and required fields.

### Tests for User Story 1 (TDD)

- [x] T006 [P] [US1] Add manifest schema validation tests against contracts/tool-manifest.openapi.yaml in llm-tooling/tests/test_manifest_contract.py
- [x] T007 [P] [US1] Add tool inventory coverage test (manifest covers all CLI commands) in llm-tooling/tests/test_manifest_contract.py
- [x] T008 [P] [US1] Add examples, risk, and idempotency coverage test in llm-tooling/tests/test_manifest_contract.py

### Implementation for User Story 1

- [x] T009 [US1] Populate llm-tooling/tool.manifest.json with auditgraph CLI tool definitions per contract schema
- [x] T010 [US1] Implement manifest loader and validator in auditgraph/utils/mcp_manifest.py

**Checkpoint**: US1 passes and is independently testable.

---

## Phase 4: User Story 2 - MCP server for auditgraph tools (Priority: P2)

**Goal**: MCP server exposes manifest tools, enforces safety rules, and normalizes errors.

**Independent Test**: Start MCP server and invoke a tool with valid and invalid inputs.

### Tests for User Story 2 (TDD)

- [x] T011 [P] [US2] Add MCP tool list test (manifest parity) in llm-tooling/tests/test_mcp_server.py
- [x] T012 [P] [US2] Add error normalization test (mapped codes) in llm-tooling/tests/test_mcp_server.py
- [x] T013 [P] [US2] Add minimum error code coverage test (assert exact required set) in llm-tooling/tests/test_mcp_server.py
- [x] T014 [P] [US2] Add read-only env var enforcement test in llm-tooling/tests/test_mcp_server.py
- [x] T015 [P] [US2] Add path-constraint enforcement test in llm-tooling/tests/test_mcp_server.py
- [x] T016 [P] [US2] Add tool logging coverage test (request ID, tool, duration, status) in llm-tooling/tests/test_mcp_server.py
- [x] T017 [P] [US2] Add performance smoke test for read tools within 5s in llm-tooling/tests/test_mcp_server.py

### Implementation for User Story 2

- [x] T018 [US2] Implement subprocess adapter with argument allowlist in llm-tooling/mcp/adapters/project.py
- [x] T019 [US2] Implement MCP server entry and tool dispatch in llm-tooling/mcp/server.py
- [x] T020 [US2] Enforce read-only mode for write/high-risk tools in llm-tooling/mcp/server.py
- [x] T021 [US2] Enforce path constraints for export-related tools in llm-tooling/mcp/adapters/project.py
- [x] T022 [US2] Emit structured tool execution logs in llm-tooling/mcp/server.py
- [x] T023 [US2] Normalize errors using auditgraph/utils/mcp_errors.py in llm-tooling/mcp/server.py

**Checkpoint**: US2 passes and is independently testable.

---

## Phase 5: User Story 3 - Skill doc and adapters (Priority: P3)

**Goal**: Skill doc and adapter bundles are generated from the manifest.

**Independent Test**: Validate skill.md sections and adapter schema bundle against the manifest.

### Tests for User Story 3 (TDD)

- [x] T024 [P] [US3] Add skill doc completeness test in llm-tooling/tests/test_skill_doc.py
- [x] T025 [P] [US3] Add adapter bundle validation test in llm-tooling/tests/test_adapters.py
- [x] T026 [P] [US3] Add determinism test for generated artifacts in llm-tooling/tests/test_adapters.py

### Implementation for User Story 3

- [x] T027 [US3] Implement skill doc generator in llm-tooling/generate_skill_doc.py
- [x] T028 [US3] Generate llm-tooling/skill.md from the manifest using llm-tooling/generate_skill_doc.py
- [x] T029 [US3] Implement adapter bundle generator in llm-tooling/generate_adapters.py
- [x] T030 [US3] Generate llm-tooling/adapters/openai.functions.json from the manifest using llm-tooling/generate_adapters.py

**Checkpoint**: US3 passes and is independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T031 [P] Validate specs/016-mcp-tools-llm-integration/quickstart.md against actual tooling behavior; update if mismatched
- [x] T032 [P] Update README.md with llm-tooling usage, regeneration, and MCP server instructions
- [x] T033 Run llm-tooling contract tests: `pytest -q llm-tooling/tests`

---

## Dependencies & Execution Order

### Dependency Graph (User Story Completion Order)

1. Phase 1 (Setup)
2. Phase 2 (Foundational) - blocks all user stories
3. US1 (P1) - manifest
4. US2 (P2) - MCP server
5. US3 (P3) - skill doc + adapters
6. Polish

### Parallel Opportunities

- Phase 1: T001 and T002 can run in parallel.
- Phase 2: T003 through T005 can run in parallel.
- US1: T006 through T008 can run in parallel.
- US2: T011 through T016 can run in parallel.
- US3: T023 through T025 can run in parallel.
- Polish: T030 and T031 can run in parallel.

### Parallel Example: User Story 2

- MCP tool list test: llm-tooling/tests/test_mcp_server.py
- Error normalization test: llm-tooling/tests/test_mcp_server.py
- Read-only enforcement test: llm-tooling/tests/test_mcp_server.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate: run the US1 tests only

### Incremental Delivery

1. Add MCP server implementation and tests (US2)
2. Add skill doc and adapter generation (US3)
3. Validate documentation and run full contract tests
