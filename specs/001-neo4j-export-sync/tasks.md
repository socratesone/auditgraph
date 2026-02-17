# Tasks: Neo4j Export and Sync

**Feature Branch**: `001-neo4j-export-sync`  
**Input**: Design documents from `/specs/001-neo4j-export-sync/`  
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included to satisfy constitution quality gates and validate determinism, idempotency, safety, and performance criteria.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths follow plan.md structure: `auditgraph/neo4j/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Neo4j module structure

- [X] T001 Create auditgraph/neo4j/ module directory with __init__.py
- [X] T002 Add initial neo4j-driver dependency entry to requirements-dev.txt for development and test execution
- [X] T003 [P] Create exports/neo4j/ default export directory
- [X] T004 [P] Create tests/fixtures/neo4j_fixtures.py for test graph data

**Checkpoint**: Neo4j module structure and dependencies in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core graph record abstraction and shared utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement GraphNodeRecord dataclass in auditgraph/neo4j/records.py with id, type, neo4j_label, name, canonical_key, profile, run_id, source_path, source_hash fields
- [X] T006 Implement GraphRelationshipRecord dataclass in auditgraph/neo4j/records.py with id, from_id, to_id, type, rule_id, confidence, authority, evidence fields
- [X] T007 Implement load_graph_nodes() function in auditgraph/neo4j/records.py that loads entities from pkg_root, applies redaction, sorts by id deterministically
- [X] T008 Implement load_graph_relationships() function in auditgraph/neo4j/records.py that loads links from pkg_root, applies redaction, filters missing nodes, sorts by (from_id, to_id, id) deterministically
- [X] T009 Implement map_entity_type_to_label() function in auditgraph/neo4j/records.py that converts entity type to `:Auditgraph<Type>` label format
- [X] T010 [P] Create test_neo4j_records.py with tests for deterministic ordering, redaction application, label mapping
- [X] T011 Verify all tests in test_neo4j_records.py pass

**Checkpoint**: Graph record abstraction complete - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Export graph for external exploration (Priority: P1) 🎯 MVP

**Goal**: Enable engineers to generate deterministic .cypher files for manual Neo4j import

**Independent Test**: Run export command on test workspace, verify output file exists, contains batched transactions, deterministic ordering

### Implementation for User Story 1

- [X] T012 [P] [US1] Create ExportSummary dataclass in auditgraph/neo4j/export.py with mode, profile, timestamp, output_path, nodes_processed, relationships_processed, skipped_count, failed_count, duration_seconds fields
- [X] T013 [P] [US1] Implement generate_export_header() function in auditgraph/neo4j/cypher_builder.py that creates file header comment with profile, timestamp, counts, format version
- [X] T014 [P] [US1] Implement generate_constraint_statements() function in auditgraph/neo4j/cypher_builder.py that creates unique constraint Cypher for all discovered labels
- [X] T015 [US1] Implement generate_node_merge_statement() function in auditgraph/neo4j/cypher_builder.py that creates parameterized MERGE with SET for single GraphNodeRecord
- [X] T016 [US1] Implement generate_relationship_merge_statement() function in auditgraph/neo4j/cypher_builder.py that creates MATCH + MERGE for single GraphRelationshipRecord
- [X] T017 [US1] Implement batch_records() utility in auditgraph/neo4j/cypher_builder.py that yields 1000-record batches from iterable
- [X] T018 [US1] Implement write_batched_cypher_file() function in auditgraph/neo4j/export.py that writes header, constraints, nodes (batched with `:begin/:commit`), relationships (batched), to output path and handles file I/O errors with actionable diagnostics
- [ ] T019 [US1] Implement export_neo4j() main function in auditgraph/neo4j/export.py that orchestrates: load config, load nodes/relationships, generate cypher file, return ExportSummary, and report partial progress if interrupted
- [X] T020 [US1] Add export-neo4j command to auditgraph/cli.py with --root, --config, --output arguments; default output path to exports/neo4j/<profile>-<run_id>.cypher when --output is omitted
- [X] T021 [P] [US1] Create test_neo4j_cypher_builder.py with tests for statement generation, batching, deterministic output
- [X] T022 [P] [US1] Create test_neo4j_export.py with tests for full export flow, deterministic ordering (SC-002), file format validation
- [X] T023 [US1] Verify export command produces valid .cypher files with correct batching and ordering
- [ ] T024 [US1] Import generated .cypher file into a test Neo4j instance and verify nodes/relationships are queryable end-to-end

**Checkpoint**: User Story 1 complete - engineers can export graphs to .cypher format and import manually

---

## Phase 4: User Story 2 - Sync graph into a Neo4j instance (Priority: P2)

**Goal**: Enable direct sync to running Neo4j instances using environment variables for connection

**Independent Test**: Run sync command with test Neo4j instance, verify nodes and relationships created, re-run and verify idempotency (no duplicates)

### Implementation for User Story 2

- [X] T025 [P] [US2] Create Neo4jConnectionProfile dataclass in auditgraph/neo4j/connection.py with uri, user, password, database, max_connection_pool_size fields
- [X] T026 [US2] Implement load_connection_from_env() function in auditgraph/neo4j/connection.py that reads NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE from environment and validates
- [X] T027 [US2] Implement create_driver() function in auditgraph/neo4j/connection.py that creates neo4j.GraphDatabase.driver from connection profile
- [X] T028 [US2] Implement ping_connection() function in auditgraph/neo4j/connection.py that runs simple query to verify connectivity
- [X] T029 [US2] Implement ensure_constraints() function in auditgraph/neo4j/sync.py that executes CREATE CONSTRAINT IF NOT EXISTS statements for all node labels
- [X] T030 [US2] Implement sync_nodes_batch() function in auditgraph/neo4j/sync.py that executes parameterized MERGE statements in write transaction for 1000-node batch
- [X] T031 [US2] Implement sync_relationships_batch() function in auditgraph/neo4j/sync.py that executes MATCH + MERGE statements in write transaction for 1000-relationship batch
- [X] T032 [US2] Implement sync_neo4j() main function in auditgraph/neo4j/sync.py that orchestrates: load connection, ping, ensure constraints, batch sync nodes, batch sync relationships, return ExportSummary
- [X] T033 [US2] Add sync-neo4j command to auditgraph/cli.py with --root, --config arguments (reads env vars for connection)
- [X] T034 [P] [US2] Create test_neo4j_connection.py with tests for env var loading, validation, driver creation, error cases
- [X] T035 [P] [US2] Create test_neo4j_sync.py with tests for constraint creation, batch sync, idempotency (SC-005), skip logic for missing nodes
- [X] T036 [US2] Verify sync command creates and updates records idempotently without duplicates

**Checkpoint**: User Story 2 complete - engineers can sync graphs directly to Neo4j instances

---

## Phase 5: User Story 3 - Safe and observable operations (Priority: P3)

**Goal**: Add dry-run mode, error diagnostics, and operation summaries for operational safety

**Independent Test**: Run sync with --dry-run flag, verify no database mutations; run with invalid credentials, verify actionable error message

### Implementation for User Story 3

- [X] T037 [US3] Add dry_run parameter to sync_nodes_batch() and sync_relationships_batch() in auditgraph/neo4j/sync.py that skips tx.commit() when enabled
- [X] T038 [US3] Update sync_neo4j() in auditgraph/neo4j/sync.py to accept dry_run parameter and set mode in ExportSummary
- [X] T039 [US3] Add --dry-run flag to sync-neo4j command in auditgraph/cli.py
- [X] T040 [US3] Implement map_neo4j_exception() function in auditgraph/neo4j/connection.py that converts ServiceUnavailable, AuthError, TransientError, ClientError to actionable error messages with diagnostic hints (check NEO4J_URI, verify credentials, etc.)
- [X] T041 [US3] Wrap driver operations in sync_neo4j() with try/except blocks that use map_neo4j_exception() for error handling
- [X] T042 [US3] Add error tracking to ExportSummary: add errors field (list of dicts with message and affected record IDs)
- [X] T043 [US3] Update CLI output formatting in cli.py to display ExportSummary with counts (processed, created, updated, skipped, failed) and duration
- [X] T044 [P] [US3] Add tests to test_neo4j_sync.py for dry-run mode (no commits), error handling (connection failures, auth errors), summary reporting
- [ ] T045 [US3] Verify dry-run produces summary without mutations, invalid credentials produce actionable errors

**Checkpoint**: User Story 3 complete - all safety and observability features functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance validation, documentation, and final quality gates

- [ ] T046 [P] Update README.md with Neo4j export/sync feature description and link to quickstart
- [X] T047 [P] Finalize dependency lock by pinning neo4j-driver to `neo4j>=5,<6` in requirements-dev.txt and removing any unbounded temporary entry from T002
- [ ] T048 Validate performance: export 100K nodes + 300K relationships completes within 2 minutes (SC-001)
- [ ] T049 Measure and record sync idempotency overhead, targeting <10% overhead versus baseline sync path
- [ ] T050 Add profile isolation test: verify export/sync only processes active profile artifacts (FR-008)
- [ ] T051 Add redaction integration test: verify sensitive fields redacted in cypher output (FR-009)
- [X] T052 Run full targeted Neo4j test suite: pytest tests/test_neo4j_*.py and ensure all tests pass (exit code 0)
- [ ] T053 Run quickstart.md validation: execute all export and sync examples from quickstart guide
- [ ] T054 Run user-acceptance validation for SC-004 with at least 10 participants using a scripted task and record timing/results
- [ ] T055 Measure SC-003 reliability over a 14-day window with at least 200 sync runs and publish completion-rate evidence
- [ ] T056 Update CHANGELOG.md with Neo4j export/sync feature addition
- [ ] T057 Update root QUICKSTART.md with Neo4j export/sync setup and command examples
- [ ] T058 Update MCP_GUIDE.md and docs/environment-setup.md with Neo4j environment variables and cypher-shell usage notes
- [X] T059 Run full repository test suite (pytest) and ensure all tests pass before completion gate
- [ ] T060 Record final test evidence (commands, exit codes, summary) in feature documentation/checklist

**Checkpoint**: All tasks complete, documentation updated, and full test suite passing for PR readiness

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T004) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T005-T011) - Can proceed once foundation ready
- **User Story 2 (Phase 4)**: Depends on Foundational (T005-T011) - Can proceed once foundation ready
- **User Story 3 (Phase 5)**: Depends on User Story 2 (T025-T036) - Extends sync with dry-run and error handling
- **Polish (Phase 6)**: Depends on all user stories (T012-T045) being complete

### User Story Dependencies

- **User Story 1 (P1 - Export)**: Depends on Foundational phase only
  - No dependencies on other stories
  - Can be implemented and tested independently
  - Delivers standalone MVP value (manual export)

- **User Story 2 (P2 - Sync)**: Depends on Foundational phase only
  - Does NOT depend on User Story 1 (separate code paths)
  - Can be implemented and tested independently
  - Reuses graph record abstraction from foundation

- **User Story 3 (P3 - Safety)**: Depends on User Story 2
  - Extends sync functionality with dry-run and error handling
  - Cannot be implemented without sync infrastructure

### Within Each User Story

**User Story 1 (Export)**:
- T012, T013, T014 (dataclasses and header generation) can run in parallel [P]
- T015-T017 (Cypher statement generation) must follow in sequence (build on each other)
- T018-T019 (file writing and orchestration) must follow T015-T017
- T020 (CLI integration) must follow T019
- T021, T022 (tests) can run in parallel [P] after implementation complete
- T023-T024 (verification) must be last

**User Story 2 (Sync)**:
- T025-T026 (connection profile) form a unit
- T027-T028 (driver creation) must follow T025-T026
- T029-T031 (sync operations) must follow T027-T028
- T032-T033 (orchestration and CLI) must follow T029-T031
- T034, T035 (tests) can run in parallel [P] after implementation complete
- T036 (verification) must be last

**User Story 3 (Safety)**:
- T037-T039 (dry-run) extend existing sync code (sequential)
- T040-T041 (error handling) extend existing sync code (sequential)
- T042-T043 (summary reporting) extend existing code (sequential)
- T044 (tests) after implementation
- T045 (verification) must be last

### Parallel Opportunities

**Within Setup (Phase 1)**:
```bash
# All setup tasks can run in parallel:
T001 (module structure) || T002 (dependencies) || T003 (export dir) || T004 (fixtures)
```

**Within Foundational (Phase 2)**:
```bash
# Dataclasses can be created in parallel:
T005 (GraphNodeRecord) || T006 (GraphRelationshipRecord)

# After dataclasses, loader functions can proceed:
T007 (load nodes) || T008 (load relationships)

# After loaders:
T009 (label mapping)

# Tests after implementation:
T010 (create tests) then T011 (verify tests)
```

**Across User Stories** (if team capacity allows):
```bash
# After Foundational phase completes, these can proceed in parallel:
Developer A: User Story 1 (T012-T024)
Developer B: User Story 2 (T025-T036)

# User Story 3 must wait for US2 to complete
```

**Within User Story 1 (Export)**:
```bash
# Parallel within US1:
T012 (ExportSummary) || T013 (header gen) || T014 (constraints)

# Then sequential:
T015 → T016 → T017 → T018 → T019 → T020

# Then parallel tests:
T021 (cypher builder tests) || T022 (export tests)

# Then verify:
T023 → T024
```

**Within User Story 2 (Sync)**:
```bash
# Parallel within US2:
T025 (ConnectionProfile) || T034 (connection tests setup)

# Then sequential implementation:
T026 → T027 → T028 → T029 → T030 → T031 → T032 → T033

# Then parallel tests:
T034 (connection tests) || T035 (sync tests)

# Then verify:
T036
```

**Within Polish (Phase 6)**:
```bash
# These can run in parallel:
T046 (README) || T047 (requirements) || T050 (profile test) || T051 (redaction test)

# Then sequential:
T048 (performance) → T049 (idempotency overhead) → T052 (targeted tests) → T053 (feature quickstart) → T054 (UAT) → T055 (reliability evidence) → T057 (root quickstart docs) → T058 (environment docs) → T059 (full suite) → T060 (evidence) → T056 (CHANGELOG)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Phase 1**: Setup (T001-T004) - ~30 minutes
2. **Phase 2**: Foundational (T005-T011) - ~2 hours
   - **CRITICAL CHECKPOINT**: Verify test_neo4j_records.py passes
3. **Phase 3**: User Story 1 (T012-T024) - ~4 hours
   - **VALIDATION**: Export test workspace, manually import to Neo4j
4. **Deploy/Demo**: Users can export graphs to .cypher format

**Total MVP Effort**: ~6-7 hours

### Incremental Delivery

1. **Foundation** (Phases 1+2) → T001-T011 complete → ~2.5 hours
2. **Add Export** (Phase 3) → T012-T024 complete → Deploy/Demo (MVP!) → ~4 hours
3. **Add Sync** (Phase 4) → T025-T036 complete → Deploy/Demo → ~4 hours
4. **Add Safety** (Phase 5) → T037-T045 complete → Deploy/Demo → ~2 hours
5. **Polish** (Phase 6) → T046-T060 complete → Final release → ~2 hours

**Total Full Feature Effort**: ~14-15 hours

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Setup + Foundational (T001-T011) - ~2.5 hours
2. **Once Foundational complete**:
  - **Developer A**: User Story 1 (T012-T024) - ~4 hours
  - **Developer B**: User Story 2 (T025-T036) - ~4 hours
3. **Developer B**: User Story 3 (T037-T045) - ~2 hours
4. **Together**: Polish (T046-T060) - ~2 hours

**Total Parallel Effort**: ~8-9 hours (vs 14-15 sequential)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 parallel tasks:

# Batch 1 - Parallel dataclass and utilities:
T012: "Create ExportSummary dataclass in auditgraph/neo4j/export.py"
T013: "Implement generate_export_header() in cypher_builder.py"
T014: "Implement generate_constraint_statements() in cypher_builder.py"

# Batch 2 - Sequential Cypher generation (build on each other):
T015: "Implement generate_node_merge_statement() in cypher_builder.py"
T016: "Implement generate_relationship_merge_statement() in cypher_builder.py"
T017: "Implement batch_records() in cypher_builder.py"

# Batch 3 - Sequential orchestration:
T018: "Implement write_batched_cypher_file() in export.py"
T019: "Implement export_neo4j() main function in export.py"
T020: "Add export-neo4j command to cli.py"

# Batch 4 - Parallel tests:
T021: "Create test_neo4j_cypher_builder.py"
T022: "Create test_neo4j_export.py"

# Verify:
T023: "Verify export command produces valid .cypher files"
T024: "Import generated .cypher file into test Neo4j and validate queryability"
```

---

## Notes

- All tasks follow TDD where applicable: write tests to verify behavior
- [P] tasks target different files and can run in parallel
- [Story] labels map tasks to user stories for independent tracking
- Each user story delivers standalone value and can be tested independently
- Foundation phase (T005-T011) is CRITICAL - all stories depend on it
- US3 extends US2 (dry-run and error handling), so US2 must complete first
- Deterministic ordering (FR-011) implemented in T007-T008
- Idempotency (FR-005, SC-005) validated in T035-T036
- Performance target (SC-001) validated in T048
- SC-003 is validated with reliability evidence in T055 (outside pure unit/integration test scope)
- SC-004 is validated as user-acceptance evidence in T054 (outside pure unit/integration test scope)
- Documentation updates for Neo4j export/sync are completed in T057-T058
- Final completion requires both targeted and full-suite test passes in T052 and T059
- Stop at any checkpoint to validate story independently before proceeding
