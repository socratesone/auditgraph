---

description: "Task list for implementing Security, Privacy, and Compliance Policies"

---

# Tasks: Security, Privacy, and Compliance Policies

**Input**: Design documents from `/specs/011-security-privacy-compliance/`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create secret-bearing fixtures in tests/fixtures/spec011/ (e.g., tests/fixtures/spec011/secret_note.md, tests/fixtures/spec011/app.log)
- [X] T002 [P] Add shared assertions/helpers for "no secret substring exists under a directory" in tests/support.py

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T003 [P] Add new error types for security/path policy failures in auditgraph/errors.py
- [X] T004 [P] Implement strict profile name validation helper (reject separators, `..`, empty) in auditgraph/utils/profile.py
- [X] T005 [P] Implement safe path enforcement helpers (resolve + ensure-within-base) in auditgraph/utils/paths.py
- [X] T006 Add security/redaction config defaults + parsing helpers in auditgraph/config.py
- [X] T007 Add security/redaction defaults to sample config in config/pkg.yaml
- [X] T008 [P] Implement profile-scoped redaction key load/create (persist under `.pkg/profiles/<profile>/secrets/redaction.key`) in auditgraph/utils/redaction.py
- [X] T009 [P] Implement deterministic redaction engine + MVP detectors in auditgraph/utils/redaction.py
- [X] T010 Implement redacting write helpers (e.g., write_json_redacted/write_text_redacted) in auditgraph/storage/safe_artifacts.py
- [X] T011 Apply redaction to ingested source metadata before persistence in auditgraph/pipeline/runner.py
- [X] T012 Ensure config snapshots never persist secret values (and never persist the redaction key) in auditgraph/storage/config_snapshot.py
- [X] T013 Enforce job output path boundary and use redacting writer for report outputs in auditgraph/jobs/reports.py
- [X] T014 Enforce export output path boundary for workspace-relative `--output` paths in auditgraph/cli.py

**Checkpoint**: Foundation ready (redaction + path policies exist; no story work before this)

---

## Phase 3: User Story 1 - Prevent secrets leakage (Priority: P1) 🎯 MVP

**Goal**: Secrets detected in inputs do not leak into derived artifacts or exports.

**Independent Test**: Run ingest/export over a fixture containing a sentinel secret and confirm the sentinel string does not appear anywhere in `.pkg/` or the exported file.

### Tests for User Story 1 (TDD)

- [X] T015 [P] [US1] Add redaction unit tests (detectors + deterministic markers) in tests/test_spec011_redaction.py
- [X] T016 [P] [US1] Add ingest integration test: secret in frontmatter/title is redacted in `.pkg/.../sources/*.json` in tests/test_spec011_ingest_redaction.py
- [X] T017 [P] [US1] Add export integration test: secret is not present in exported JSON output in tests/test_spec011_export_redaction.py

### Implementation for User Story 1

- [X] T018 [US1] Redact entity name/canonical inputs before persistence and before ID derivation where applicable in auditgraph/extract/entities.py
- [X] T019 [US1] Redact log claim signatures before hashing and persistence (avoid fingerprint leaks) in auditgraph/extract/entities.py
- [X] T020 [P] [US1] Apply redaction to JSON export payload fields in auditgraph/export/json.py
- [X] T021 [P] [US1] Apply redaction to DOT export labels in auditgraph/export/dot.py
- [X] T022 [P] [US1] Apply redaction to GraphML export labels in auditgraph/export/graphml.py
- [X] T023 [US1] Update existing export tests for payload shape changes in tests/test_user_story_extract_export_jobs.py, tests/test_cli_integration.py, tests/test_smoke.py

**Checkpoint**: US1 passes and can be demonstrated independently.

---

## Phase 4: User Story 2 - Keep profiles isolated (Priority: P2)

**Goal**: A single active profile cannot read/write outside `.pkg/profiles/<active-profile>/...`, and unsafe output paths are rejected.

**Independent Test**: Provide a malicious profile name or a `../` output path and verify the command fails closed without writing outside the workspace.

### Tests for User Story 2 (TDD)

- [X] T024 [P] [US2] Add test: invalid `active_profile` (e.g., `../x`) is rejected when computing `pkg_root` in tests/test_spec011_profile_isolation.py
- [X] T025 [P] [US2] Add CLI test: `auditgraph export --output ../evil.json` fails closed in tests/test_spec011_export_path_safety.py
- [X] T026 [US2] Add jobs test: job `output.path` traversal (e.g., `../evil.md`) is rejected in tests/test_user_story_job_outputs.py

### Implementation for User Story 2

- [X] T027 [US2] Enforce profile validation in auditgraph/config.py
- [X] T028 [US2] Enforce profile validation at the filesystem boundary in auditgraph/storage/artifacts.py
- [X] T029 [US2] Enforce job output paths stay within allowed base (at least under `<root>/exports/`) in auditgraph/jobs/reports.py
- [X] T030 [US2] Enforce export output paths stay within allowed base (default `<root>/exports/subgraphs/`) in auditgraph/cli.py
- [X] T031 [US2] Prevent include_paths from escaping workspace root by default in auditgraph/ingest/scanner.py
- [X] T032 [US2] Prevent manual import targets from escaping workspace root by default in auditgraph/ingest/importer.py

**Checkpoint**: US2 passes and is independently testable.

---

## Phase 5: User Story 3 - Share clean-room exports (Priority: P3)

**Goal**: Default exports are redacted and contain required metadata for safe sharing.

**Independent Test**: Export JSON and verify it includes `export_metadata` with required fields and an accurate redaction summary.

### Tests for User Story 3 (TDD)

- [X] T033 [P] [US3] Add tests validating `export_metadata` schema + `clean_room=true` + redaction_summary counts in tests/test_spec011_export_metadata.py

### Implementation for User Story 3

- [X] T034 [US3] Implement export metadata helper (root_id, created_at, policy version, summary) in auditgraph/utils/export_metadata.py
- [X] T035 [US3] Add `export_metadata` block to JSON exports and compute `redaction_summary` in auditgraph/export/json.py
- [X] T036 [US3] Keep CLI contract stable while exporting metadata (ensure CLI still returns `{format, output}`) in auditgraph/cli.py

**Checkpoint**: US3 passes and produces clean-room exports.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T037 [P] Document new redaction/export behavior in README.md
- [X] T038 Run full test suite and fix regressions caused by contract changes: `pytest -q`
- [X] T039 Validate specs/011-security-privacy-compliance/quickstart.md against real CLI behavior; update quickstart if mismatched

---

## Dependencies & Execution Order

### Dependency Graph (User Story Completion Order)

1. Phase 1 (Setup)
2. Phase 2 (Foundational) — blocks all user stories
3. US1 (P1) — establishes redaction correctness
4. US2 (P2) — establishes isolation + path safety correctness
5. US3 (P3) — builds clean-room exports on top of redaction + safe output paths
6. Polish

### Parallel Opportunities

- Phase 2: T003, T004, T005, T008, T009 can run in parallel.
- US1: T015–T017 can run in parallel.
- US2: T024–T026 can run in parallel.

### Parallel Example: User Story 1

- Redaction unit tests: tests/test_spec011_redaction.py
- Ingest redaction integration test: tests/test_spec011_ingest_redaction.py
- Export redaction integration test: tests/test_spec011_export_redaction.py

### Parallel Example: User Story 2

- Profile traversal test: tests/test_spec011_profile_isolation.py
- Export output traversal CLI test: tests/test_spec011_export_path_safety.py
- Jobs output traversal test: tests/test_user_story_job_outputs.py

### Parallel Example: User Story 3

- Export metadata schema tests: tests/test_spec011_export_metadata.py
- Export metadata helper implementation: auditgraph/utils/export_metadata.py

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 + Phase 2
2. Implement US1 with strict TDD (tests first), then run `pytest -q`
3. Validate the sentinel secret does not appear under `.pkg/` or exports

### Incremental Delivery

1. Add US2 (profile/path isolation) and re-run full suite
2. Add US3 (export metadata) and re-run full suite

