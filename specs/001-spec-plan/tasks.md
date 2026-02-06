---

description: "Task list for Auditgraph spec implementation"
---

# Tasks: Auditgraph Spec Implementation

**Input**: Design documents from `/specs/001-spec-plan/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

**Tests**: Not requested in the feature specification; no test tasks included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US14)
- Each task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish core structure and CLI wiring

- [X] T001 Create package submodules for pipeline stages in auditgraph/ingest/, auditgraph/normalize/, auditgraph/extract/, auditgraph/link/, auditgraph/index/, auditgraph/query/, auditgraph/pipeline/, auditgraph/storage/, auditgraph/plugins/, auditgraph/jobs/
- [X] T002 Add configuration loader and defaults in auditgraph/config.py and config/pkg.yaml
- [X] T003 [P] Extend CLI command registry in auditgraph/cli.py for ingest/extract/link/index/query/rebuild/diff/export/jobs
- [X] T004 [P] Add structured logging bootstrap in auditgraph/logging.py and wire to auditgraph/cli.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Deterministic utilities and artifact I/O required by all stories

- [X] T005 Implement path normalization utilities in auditgraph/normalize/paths.py
- [X] T006 Implement text normalization utilities in auditgraph/normalize/text.py
- [X] T007 Implement hashing helpers (sha256, canonical bytes) in auditgraph/storage/hashing.py
- [X] T008 Implement manifest data models in auditgraph/storage/manifests.py
- [X] T009 Implement artifact read/write helpers in auditgraph/storage/artifacts.py
- [X] T010 Implement deterministic sorting helpers in auditgraph/utils/sort.py
- [X] T011 Implement pipeline runner orchestration in auditgraph/pipeline/runner.py
- [X] T012 Implement plugin registry and loader in auditgraph/plugins/registry.py
- [X] T013 Implement base error types in auditgraph/errors.py

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 (Priority: P1) 🎯 MVP

**Story**: As an engineer, I can point the PKG at a workspace folder and it indexes Markdown notes and Git repos without internet access.

**Independent Test**: Running `auditgraph ingest` creates a deterministic ingest manifest and source artifacts under .pkg/.

- [X] T014 [US1] Implement file discovery and ignore rules in auditgraph/ingest/scanner.py
- [X] T015 [P] [US1] Implement Markdown/plain-text parser in auditgraph/ingest/parsers.py
- [X] T016 [US1] Implement source record builder in auditgraph/ingest/sources.py
- [X] T017 [US1] Implement ingest manifest writer in auditgraph/ingest/manifest.py
- [X] T018 [US1] Wire ingest stage into pipeline in auditgraph/pipeline/runner.py
- [X] T019 [US1] Wire `ingest` CLI command in auditgraph/cli.py

---

## Phase 4: User Story 2 (Priority: P2)

**Story**: As an engineer, I can search for a symbol name and find where it is defined, referenced, and discussed in notes.

**Independent Test**: Running `auditgraph query --q "symbol"` returns deterministic results with explanations and source pointers.

- [X] T020 [US2] Implement basic code symbol extraction in auditgraph/extract/code_symbols.py
- [X] T021 [P] [US2] Implement entity/claim builders in auditgraph/extract/entities.py
- [X] T022 [US2] Implement extract stage writer in auditgraph/extract/manifest.py
- [X] T023 [US2] Implement BM25 keyword index builder in auditgraph/index/bm25.py
- [X] T024 [US2] Implement keyword query engine in auditgraph/query/keyword.py
- [X] T025 [US2] Add query output with explanations in auditgraph/cli.py

---

## Phase 5: User Story 3 (Priority: P2)

**Story**: As an engineer, I can open a node and see the exact sources and snippets that created each claim.

**Independent Test**: Running `auditgraph node <id>` prints sources and evidence ranges for the node.

- [X] T026 [US3] Implement entity/claim loader in auditgraph/storage/loaders.py
- [X] T027 [US3] Implement node view formatter in auditgraph/query/node_view.py
- [X] T028 [US3] Add `node` CLI command in auditgraph/cli.py

---

## Phase 6: User Story 4 (Priority: P2)

**Story**: As an engineer, I can see a neighborhood graph of a concept (1–2 hops) filtered by link types.

**Independent Test**: Running `auditgraph neighbors <id> --depth 2` returns deterministic adjacency results.

- [X] T029 [US4] Implement link adjacency builder in auditgraph/link/adjacency.py
- [X] T030 [US4] Implement neighbors query in auditgraph/query/neighbors.py
- [X] T031 [US4] Add `neighbors` CLI command in auditgraph/cli.py

---

## Phase 7: User Story 5 (Priority: P2)

**Story**: As an engineer, I can capture an ADR note template and have decisions extracted into a decision index deterministically.

**Independent Test**: Running `auditgraph extract` on ADR notes produces decision claims and index entries.

- [X] T032 [US5] Implement ADR template parser in auditgraph/extract/adr.py
- [X] T033 [US5] Implement decision index writer in auditgraph/index/decisions.py
- [X] T034 [US5] Wire ADR extraction into extract stage in auditgraph/extract/manifest.py

---

## Phase 8: User Story 6 (Priority: P2)

**Story**: As an engineer, I can ingest debugging logs and extract error signatures, stack traces, and implicated modules.

**Independent Test**: Running `auditgraph extract` on log files produces error signature claims with sources.

- [X] T035 [US6] Implement log signature extractor in auditgraph/extract/logs.py
- [X] T036 [US6] Add log entity/claim creation in auditgraph/extract/entities.py
- [X] T037 [US6] Wire log extraction into extract stage in auditgraph/extract/manifest.py

---

## Phase 9: User Story 7 (Priority: P2)

**Story**: As an engineer, I can run “rebuild” and get identical derived outputs given the same inputs and config.

**Independent Test**: Running `auditgraph rebuild` twice yields byte-identical artifacts and manifests.

- [X] T038 [US7] Implement run_id and replay log in auditgraph/pipeline/runner.py
- [X] T039 [US7] Add `rebuild` CLI command in auditgraph/cli.py

---

## Phase 10: User Story 8 (Priority: P3)

**Story**: As an engineer, I can diff two runs and see exactly what changed.

**Independent Test**: Running `auditgraph diff --run A --run B` produces a deterministic change report.

- [X] T040 [US8] Implement run diff utility in auditgraph/query/diff.py
- [X] T041 [US8] Add `diff` CLI command in auditgraph/cli.py

---

## Phase 11: User Story 9 (Priority: P3)

**Story**: As an engineer, I can maintain separate profiles (work/personal) with no cross-contamination.

**Independent Test**: Running with different profiles writes to isolated storage roots.

- [X] T042 [US9] Implement profile config loader in auditgraph/config.py
- [X] T043 [US9] Enforce profile isolation in auditgraph/storage/artifacts.py

---

## Phase 12: User Story 10 (Priority: P3)

**Story**: As an engineer, I can export a subgraph (project-scoped) to JSON/DOT/GraphML for sharing.

**Independent Test**: Running `auditgraph export --format json|dot|graphml` produces deterministic files.

- [X] T044 [US10] Implement export JSON in auditgraph/export/json.py
- [X] T045 [P] [US10] Implement export DOT in auditgraph/export/dot.py
- [X] T046 [P] [US10] Implement export GraphML in auditgraph/export/graphml.py
- [X] T047 [US10] Add `export` CLI command in auditgraph/cli.py

---

## Phase 13: User Story 11 (Priority: P3)

**Story**: As an engineer, I can add a custom deterministic extraction rule as a plugin.

**Independent Test**: A configured plugin runs during extract and generates artifacts with provenance.

- [X] T048 [US11] Implement plugin schema in auditgraph/plugins/schema.py
- [X] T049 [US11] Load extractor plugins from config in auditgraph/plugins/registry.py
- [X] T050 [US11] Document example extractor plugin in docs/plugins/extractor_example.md

---

## Phase 14: User Story 12 (Priority: P3)

**Story**: As an engineer, I can request optional semantic search and still keep outputs reproducible and explainable.

**Independent Test**: Enabling semantic search produces deterministic scores with stable tie-breaks.

- [X] T051 [US12] Implement semantic index interface and flag in auditgraph/index/semantic.py
- [X] T052 [US12] Add deterministic score rounding/tie-break in auditgraph/query/ranking.py
- [X] T053 [US12] Wire semantic toggle into config and query path in auditgraph/config.py and auditgraph/query/keyword.py

---

## Phase 15: User Story 13 (Priority: P3)

**Story**: As an engineer, I can ask “why is note A linked to note B?” and see the rule and evidence.

**Independent Test**: Running `auditgraph why-connected --from A --to B` returns rule id and evidence pointers.

- [X] T054 [US13] Implement link explanation resolver in auditgraph/query/why_connected.py
- [X] T055 [US13] Add `why-connected` CLI command in auditgraph/cli.py

---

## Phase 16: User Story 14 (Priority: P3)

**Story**: As an engineer, I can run a daily digest of changes since yesterday and store it as a plain-text artifact.

**Independent Test**: Running `auditgraph jobs run daily_digest` writes a deterministic report to exports/.

- [X] T056 [US14] Implement jobs config loader in auditgraph/jobs/config.py
- [X] T057 [US14] Implement scheduler runner in auditgraph/jobs/runner.py
- [X] T058 [US14] Implement changed-since report in auditgraph/jobs/reports.py
- [X] T059 [US14] Add `jobs run` CLI command in auditgraph/cli.py

---

## Phase 17: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting refinements and documentation updates

- [X] T060 [P] Update README.md with command examples and pipeline notes
- [X] T061 [P] Update docs/spec/00-overview.md to link execution artifacts
- [X] T062 Run quickstart validation steps and record any fixes in specs/001-spec-plan/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phases 3–16)**: Depend on Foundational
- **Polish (Phase 17)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: No dependencies after Foundational
- **US2–US7 (P2)**: Can start after Foundational; US2 benefits from US1 ingest artifacts
- **US8–US14 (P3)**: Can start after Foundational; may integrate with earlier artifacts

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel
- Foundational tasks marked [P] can run in parallel
- Within a user story, tasks marked [P] can run in parallel if they touch different files

---

## Parallel Example: User Story 2

- T020 Implement basic code symbol extraction in auditgraph/extract/code_symbols.py
- T021 Implement entity/claim builders in auditgraph/extract/entities.py
- T023 Implement BM25 keyword index builder in auditgraph/index/bm25.py

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. Validate US1 independently via `auditgraph ingest`

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate ingest output
3. Add US2–US7 → validate search and core graph navigation
4. Add US8–US14 → advanced features, exports, automation
