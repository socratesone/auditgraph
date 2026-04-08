# Tasks: Security Hardening (Phases 2-4)

**Input**: Design documents from `/specs/027-security-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-commands.md, contracts/mcp-validation-errors.md, contracts/postcondition-manifest.md, contracts/detector-categories.md, quickstart.md

**Tests**: Test tasks are included because Constitution Principle III (Test-Driven Development) is NON-NEGOTIABLE. Every implementation task has a preceding failing-test task. No production code is written before a failing test exists.

**Organization**: Tasks are grouped by user story. Phase 1 is shared setup; Phase 2 is foundational helpers blocking the user stories; Phases 3-10 are one per user story in priority order; Phase 11 is polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1 through US8). Setup/Foundational/Polish phases have no story label.
- All paths are repository-relative from `/home/socratesone/socratesone/auditgraph/`.

## Path Conventions

- Production code: `auditgraph/` (Python package root)
- MCP layer: `llm-tooling/mcp/`
- Tests: `tests/test_spec027_*.py`, following the existing spec-based naming convention
- Contracts and design docs: `specs/027-security-hardening/`

---

## Phase 1: Setup (dependency baseline)

Tasks in this phase must complete before any user story can be implemented, because the new runtime dependency is a prerequisite for User Story 2 (MCP validation) and the pinned parser versions are a prerequisite for the entire test suite to run reproducibly.

- [ ] T001 Add `jsonschema>=4,<5` to the `dependencies` list in `pyproject.toml` as a new runtime dependency (FR-030). Leave the existing dependency order untouched; append at the end of the list.
- [ ] T002 Add lower-bound pins for `pyyaml>=6.0.3`, `pypdf>=6.9.1`, and `python-docx>=1.2.0` in the `dependencies` list in `pyproject.toml` (FR-029). Leave the existing entries in place; replace the bare `"pyyaml"`, `"pypdf"`, `"python-docx"` with their pinned forms. No upper bounds unless a specific incompatibility is discovered during Phase 7 or Phase 10 testing.
- [ ] T003 Run `pip install -e .` from the repo root to install the new `jsonschema` dependency and verify the parser pins resolve to acceptable versions. Confirm `python -c "import jsonschema; print(jsonschema.__version__)"` returns a version in `[4.0, 5.0)`.
- [ ] T004 Write failing test `tests/test_spec027_dependency_baseline.py` that parses `pyproject.toml` (using stdlib `tomllib` on Python 3.11+ or `tomli` fallback on 3.10) and asserts: (a) `jsonschema>=4,<5` is present, (b) `pyyaml` has a `>=6.0.3` lower bound, (c) `pypdf` has a `>=6.9.1` lower bound, (d) `python-docx` has a `>=1.2.0` lower bound. Run it to confirm it passes after T001+T002.

**Checkpoint**: `pyproject.toml` is updated, `jsonschema` is installed in the venv, and `tests/test_spec027_dependency_baseline.py` is green.

---

## Phase 2: Foundational (shared primitives blocking all user stories)

The helpers below are pure-function additions reused by multiple user stories. They must land before the tests in Phases 3-10 can exercise shared behavior. Each has a paired failing test.

- [ ] T005 Write failing test `tests/test_spec027_skip_reason_constant.py` that imports `SKIP_REASON_SYMLINK_REFUSED` from `auditgraph.ingest.policy` and asserts its string value is exactly `"symlink_refused"` (matches the value required by FR-002 and the data-model).
- [ ] T006 Add `SKIP_REASON_SYMLINK_REFUSED = "symlink_refused"` constant to `auditgraph/ingest/policy.py` next to the existing `SKIP_REASON_*` constants. Run T005 to confirm it passes.
- [ ] T007 [P] Write failing test `tests/test_spec027_paths_helper.py` covering four cases for a helper function `contained_symlink_target(path, base)` in `auditgraph/utils/paths.py`: (a) a file inside `base` returns the resolved path, (b) a symlink to a file outside `base` raises `PathPolicyError`, (c) a broken symlink (target does not exist) raises `PathPolicyError`, (d) a symlink chain where the final target escapes raises `PathPolicyError`. Use `tmp_path` fixture to build the symlink structures.
- [ ] T008 Add `contained_symlink_target(path: Path, base: Path, *, label: str = "ingest path") -> Path` to `auditgraph/utils/paths.py`. The implementation is a one-liner delegating to existing `ensure_within_base` after calling `path.resolve(strict=False)`. Run T007 to confirm it passes.
- [ ] T009 [P] Write failing test `tests/test_spec027_validation_module_skeleton.py` that imports `validate`, `ValidationFailed`, `DEFAULT_MAX_STRING_LENGTH` from `llm_tooling.mcp.validation` and asserts: (a) `DEFAULT_MAX_STRING_LENGTH == 4096`, (b) `ValidationFailed` is an Exception subclass with a `to_envelope()` method, (c) `validate` exists and is callable. Do not test behavior yet (Phase 4 does that).
- [ ] T010 Create `llm-tooling/mcp/validation.py` with (a) the `DEFAULT_MAX_STRING_LENGTH = 4096` module constant, (b) a `ValidationFailed(Exception)` class with a stub `to_envelope()` method returning `{"error": {"code": "validation_failed", "tool": "", "field": "", "reason": ""}}`, (c) a stub `validate(tool_schema, payload, *, tool_name)` function that accepts the arguments and does nothing (to be filled in during Phase 4). Run T009 to confirm it passes.

**Checkpoint**: Skip reason constant, symlink containment helper, and MCP validation module skeleton are in place. All foundational tests green. User stories can now begin in parallel where their file surfaces don't overlap.

---

## Phase 3: User Story 1 — Hostile workspace ingest is contained (P1)

**Story goal**: `auditgraph ingest` and `auditgraph import` refuse symlinks that escape the workspace root, emit `symlink_refused` in the manifest, and surface a stderr summary line. Reserved `--allow-symlinks` flag raises `NotImplementedError`.

**Independent test**: Create a workspace with `notes/leak.md → /tmp/outside/secret.txt`, run ingest, confirm (a) manifest shows `skip_reason: "symlink_refused"`, (b) stderr contains the `WARN: refused N symlinks...` line, (c) no artifact in `.pkg/` references the target content, (d) intra-workspace symlinks still process normally.

### Tests for User Story 1

- [ ] T011 [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_ingest_refuses_escaping_symlink` that builds a `tmp_path` workspace with an escaping symlink, runs `PipelineRunner().run_ingest(...)`, asserts the ingest manifest contains one source record with `skip_reason == "symlink_refused"`, and asserts `/tmp/outside/secret.txt` contents do NOT appear in any shard under `tmp_path/.pkg/`.
- [ ] T012 [P] [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_ingest_processes_intrawork_symlink` that creates an intra-workspace symlink (target stays inside the workspace), runs ingest, and asserts the symlinked file IS ingested normally. This guards against regressing FR-003.
- [ ] T013 [P] [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_ingest_handles_broken_symlink` that creates a symlink to a non-existent target, runs ingest, and asserts the file is skipped with `symlink_refused` (not a crash).
- [ ] T014 [P] [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_ingest_stderr_warning` that captures `sys.stderr` during ingest of a workspace with 2 escaping symlinks and asserts exactly one line matching `WARN: refused 2 symlinks pointing outside .* \(see manifest for details\)`.
- [ ] T015 [P] [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_import_refuses_escaping_symlink` mirroring T011 but calling `run_import(targets=[...])` instead of `run_ingest`.
- [ ] T016 [P] [US1] Write failing test `tests/test_spec027_symlink_containment.py::test_allow_symlinks_flag_raises` that invokes the CLI via `subprocess` or the argparse dispatch path with `--allow-symlinks` and asserts the command raises `NotImplementedError` (or exits non-zero with a message mentioning the issue tracker). Verifies FR-004a — the flag must NOT be silently accepted as a no-op.

### Implementation for User Story 1

- [ ] T017 [US1] Modify `auditgraph/ingest/scanner.py:discover_files` to call `contained_symlink_target(path, root)` on each path yielded by `base.rglob("*")` before adding it to the file list. Catch `PathPolicyError` and collect the refused paths in a new return value. Change the return signature from `list[Path]` to `tuple[list[Path], list[Path]]` where the second list is refused-symlink paths, OR thread the refused list through the existing manifest-building flow. Whichever approach preserves the current API most cleanly; consult the existing call site in `pipeline/runner.py:141` to decide.
- [ ] T018 [US1] Modify `auditgraph/ingest/importer.py:collect_import_paths` to apply the same `contained_symlink_target` check. This file mirrors `scanner.py`; the change is parallel and uses the same helper.
- [ ] T019 [US1] Modify `auditgraph/pipeline/runner.py:run_ingest` to construct a refused-symlink source-record with `skip_reason=SKIP_REASON_SYMLINK_REFUSED` for each refused path, append it to `records`, and add it to `source_payloads` with a minimal metadata dict so the manifest-write loop picks it up. Then, at the end of `run_ingest` (after the existing `write_json_redacted` loop), emit the single stderr warning line if any refused paths were collected. Format: `WARN: refused N symlinks pointing outside <resolved_root> (see manifest for details)`. Write via `sys.stderr.write(...)`, not `print`, to avoid interfering with `_emit` stdout output.
- [ ] T020 [US1] Apply the equivalent change to `auditgraph/pipeline/runner.py:run_import` (which is structurally parallel to `run_ingest`). Reuse the same helper logic so the stderr warning and manifest skip-reason emission are identical between the two code paths.
- [ ] T021 [US1] Modify `auditgraph/cli.py` to register `--allow-symlinks` as a boolean switch on the `ingest` and `import` subparsers. In the dispatch handler for each, check `args.allow_symlinks` first and if `True` raise `NotImplementedError("--allow-symlinks is reserved for forward compatibility; current Phase 2 refuses escaping symlinks unconditionally. File an issue at https://github.com/socratesone/auditgraph/issues to discuss your use case.")` before any pipeline invocation. The flag's `help=` text should mention the reservation.
- [ ] T022 [US1] Run all Phase 3 tests (`pytest tests/test_spec027_symlink_containment.py -v`) and confirm all six green. Run the full suite with `pytest tests/ -q` and confirm no regressions in the existing 805+ tests.

**Checkpoint**: User Story 1 is independently complete and testable. The symlink containment feature can be demoed by following step 1 of `quickstart.md`.

---

## Phase 4: User Story 2 — MCP tool calls are bounded by their declared contract (P1)

**Story goal**: Every MCP tool-call payload is validated against the target tool's `input_schema` using `jsonschema` before any subprocess is invoked. Validation failures return a structured error envelope and never dispatch to the CLI.

**Independent test**: For every tool in `llm-tooling/tool.manifest.json`, submitting an unknown key, a type-mismatched value, or an oversized string produces the documented error envelope and `subprocess.run` is never called.

### Tests for User Story 2

- [ ] T023 [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_rejects_unknown_key` that submits `{"unknown_key": "value"}` to `execute_tool("ag_version", ...)` and asserts the response has `error.code == "validation_failed"`, `error.field == ""`, and `error.reason.startswith("unknown property")`. Use `unittest.mock.patch` to replace `subprocess.run` (or `adapter.run_command`) with a `MagicMock` and assert it was NEVER called.
- [ ] T024 [P] [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_rejects_type_mismatch` that submits `{"q": 42}` to `execute_tool("ag_query", ...)`, asserts `error.reason.startswith("expected string")`, and asserts the rejected integer value `42` does NOT appear anywhere in the response JSON.
- [ ] T025 [P] [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_rejects_oversized_string` that submits `{"q": "A" * (DEFAULT_MAX_STRING_LENGTH + 1)}` and asserts `error.reason.startswith("exceeds maxLength")`. Also assert the rejected value (5000+ A's) does NOT appear in the envelope.
- [ ] T026 [P] [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_positive_case_still_passes` that submits a well-formed payload to a simple read-only tool (`ag_version` with `{}`) and asserts no `"error"` key in the response. Confirms the validator does not over-reject.
- [ ] T027 [P] [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_every_tool_has_validation_coverage` that loads `llm-tooling/tool.manifest.json`, iterates over every tool, and for each tool runs the three rejection cases (unknown key, type mismatch if there is a string property, oversized string if there is a string property). This is the inventory guard required by FR-009 — it fails when a new tool is added to the manifest without automatically receiving validation coverage.
- [ ] T028 [P] [US2] Write failing test `tests/test_spec027_mcp_payload_validation.py::test_rejection_does_not_echo_instance` that submits a payload with a secret-shaped string (`{"q": "password=SENTINEL_XYZ"}` against a schema that will reject it somehow, e.g., via maxLength of 5). Assert `"SENTINEL_XYZ"` does NOT appear anywhere in the error envelope. Verifies the no-instance-echo rule in `contracts/mcp-validation-errors.md`.

### Implementation for User Story 2

- [ ] T029 [US2] Implement `llm-tooling/mcp/validation.py:validate(tool_schema, payload, *, tool_name)` to (a) apply the server-level `DEFAULT_MAX_STRING_LENGTH` default to any string property lacking a `maxLength`, (b) run `jsonschema.Draft7Validator(tool_schema).validate(payload)`, (c) catch `jsonschema.ValidationError` and translate via `_translate_error(err, tool_name)` to a `ValidationFailed` exception, (d) raise the `ValidationFailed` (which carries the error envelope via `to_envelope()`).
- [ ] T030 [US2] Implement `llm-tooling/mcp/validation.py:_translate_error(err, tool_name)` per the translation table in `contracts/mcp-validation-errors.md`. Use a dict dispatch keyed on `err.validator` (`"type"`, `"required"`, `"additionalProperties"`, `"maxLength"`, `"minLength"`, `"maximum"`, `"minimum"`, `"enum"`, `"pattern"`). Fallback for unknown validators is `f"validation failed: {err.validator}"`. **Critical**: never interpolate `err.instance` into any reason string.
- [ ] T031 [US2] Update `llm-tooling/mcp/validation.py:ValidationFailed` to carry `tool_name`, `field`, and `reason` attributes and implement `to_envelope()` to return the documented shape: `{"error": {"code": "validation_failed", "tool": self.tool_name, "field": self.field, "reason": self.reason}}`.
- [ ] T032 [US2] Modify `llm-tooling/mcp/server.py:execute_tool` to call `validation.validate(tool.get("input_schema", {}), payload, tool_name=tool_name)` immediately after `_enforce_read_only(tool)` and before `adapter = _load_adapter()`. Catch `validation.ValidationFailed` and return `exc.to_envelope()`. Verify the subprocess branch is still reached for valid payloads.
- [ ] T033 [US2] Review `llm-tooling/tool.manifest.json` and add explicit `"maxLength"` constraints to every string parameter that lacks one. For parameters where a specific maximum is unclear, leave the field absent and rely on `DEFAULT_MAX_STRING_LENGTH`. Document this decision in `specs/027-security-hardening/contracts/mcp-validation-errors.md` if any changes are needed during the review (the file already describes the default-fallback behavior).
- [ ] T034 [US2] Run `python llm-tooling/generate_skill_doc.py && python llm-tooling/generate_adapters.py` to regenerate the MCP skill document and OpenAI adapters after any manifest changes in T033.
- [ ] T035 [US2] Run all Phase 4 tests (`pytest tests/test_spec027_mcp_payload_validation.py -v`) plus the existing MCP contract tests in `llm-tooling/tests/` and confirm everything green.

**Checkpoint**: User Story 2 is independently complete. MCP tool calls now validate against their declared contracts. Demo via step 3 of `quickstart.md`.

---

## Phase 5: User Story 3 — Neo4j export path is contained (P2)

**Story goal**: `auditgraph export-neo4j --output <path>` enforces the same `ensure_within_base` check that `auditgraph export` already applies. External absolute paths are refused with the documented error shape.

**Independent test**: `auditgraph export-neo4j --output /tmp/attacker.cypher` fails with a path-containment error; `--output exports/neo4j/my.cypher` succeeds; omitting `--output` writes to a deterministic default.

### Tests for User Story 3

- [ ] T036 [US3] Write failing test `tests/test_spec027_export_neo4j_containment.py::test_external_absolute_output_refused` that builds a minimal workspace (via existing fixture helpers), runs `auditgraph export-neo4j --output /tmp/escape.cypher`, and asserts the command exits non-zero with an error message containing "must remain within" (matching the existing `export` path-containment error shape).
- [ ] T037 [P] [US3] Write failing test `tests/test_spec027_export_neo4j_containment.py::test_workspace_relative_output_accepted` that runs `auditgraph export-neo4j --output exports/neo4j/out.cypher` from a workspace root and asserts the file is created at the expected resolved location and exit code is 0.
- [ ] T038 [P] [US3] Write failing test `tests/test_spec027_export_neo4j_containment.py::test_default_output_path` that runs `auditgraph export-neo4j` with no `--output` flag and asserts the file is created at `<root>/exports/neo4j/export.cypher`.

### Implementation for User Story 3

- [ ] T039 [US3] Modify the `export-neo4j` dispatch branch in `auditgraph/cli.py` (around line 443-449) to mirror the `export` handler at lines 359-389. Specifically: (a) compute `export_base = (root / "exports" / "neo4j").resolve()`, (b) if `args.output` is given, resolve it relative to root if not absolute, and call `ensure_within_base(resolved, export_base, label="neo4j output path")`, (c) if `args.output` is omitted, default to `export_base / "export.cypher"`. Pass the resolved path to `export_neo4j(...)`.
- [ ] T040 [US3] Run Phase 5 tests (`pytest tests/test_spec027_export_neo4j_containment.py -v`) and the existing export tests (`pytest tests/test_export_neo4j*.py -v` or equivalent) to confirm no regressions in the sister command's behavior.

**Checkpoint**: User Story 3 is independently complete. Demo via step 4 of `quickstart.md`.

---

## Phase 6: User Story 4 — Redaction catches modern credential formats (P2)

**Story goal**: The redactor detects and scrubs AWS, Google, Anthropic, OpenAI, Stripe, GitHub fine-grained PAT, and `gh[opsur]_` tokens, plus new credential-keyword variants (`aws_access_key_id`, `auth_token`, etc.). New matches appear under the new `cloud_keys` category; GitHub/Slack remain under `vendor_token`.

**Independent test**: A document containing one instance of each format is ingested; no sentinel survives in any shard; the summary report shows both `cloud_keys` and `vendor_token` entries with non-zero counts.

### Tests for User Story 4

- [ ] T041 [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_aws_access_key_detected` that feeds `"Some context AKIAIOSFODNN7EXAMPLE more text"` to `Redactor.redact_text(...)` and asserts (a) the returned text does NOT contain `AKIAIOSFODNN7EXAMPLE`, (b) the summary has `by_category["cloud_keys"] >= 1`.
- [ ] T042 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_google_api_key_detected` with `AIzaSyD-EXAMPLE-ex4mpleKey-ABCDEFGHIJK1234` (39 chars total). Same assertion shape as T041.
- [ ] T043 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_anthropic_key_detected` with `sk-ant-api03-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXA_xyz`.
- [ ] T044 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_openai_key_detected` with both `sk-proj-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexample` (project-scoped) and `sk-EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0123` (legacy 48-char).
- [ ] T045 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_stripe_key_detected` with `sk_live_EXAMPLEexampleEXAMPLEex`.
- [ ] T046 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_benign_strings_not_matched` (the negative test per FR-015) feeding `"my AKIA_planning notes"`, `"sk-proj is a directory"`, `"Mozilla/5.0 (AIza is not a key)"` — none should match. This guards against over-aggressive regexes.
- [ ] T047 [P] [US4] Write failing test `tests/test_spec027_cloud_keys_detectors.py::test_category_is_cloud_keys_not_vendor_token` that ingests a document containing one AWS key and one `ghp_` token, then asserts `by_category["cloud_keys"] == 1` AND `by_category["vendor_token"] == 1` as INDEPENDENT entries. Verifies Clarification Q6.
- [ ] T048 [P] [US4] Write failing test `tests/test_spec027_credential_kv_variants.py::test_new_keyword_variants_detected` feeding text containing `aws_access_key_id=ABC`, `auth_token=XYZ`, `passwd=foo`, `refresh_token: bar`, `bearer=baz`, `auth=qux`. Assert all six substring values are absent from the redacted output and `by_category["credential"] >= 6`.
- [ ] T049 [P] [US4] Write failing test `tests/test_spec027_credential_kv_variants.py::test_existing_keywords_still_detected` feeding the pre-Spec-027 keywords (`password=`, `secret:`, `api_key=`) and asserting they still redact — regression guard for FR-018's intent applied to credential_kv.
- [ ] T050 [P] [US4] Write failing test `tests/test_spec027_credential_kv_variants.py::test_new_github_prefixes_in_vendor_token` feeding `github_pat_11ABCDEFG0abc...`, `gho_abc...`, `ghu_abc...`, `ghs_abc...`, `ghr_abc...`, `xoxe.xoxp-1-abc...` and asserting all are redacted and `by_category["vendor_token"] >= 6`.

### Implementation for User Story 4

- [ ] T051 [US4] Extend the `credential_kv` detector's regex in `auditgraph/utils/redaction.py:_default_detectors()` to include the new keywords listed in `contracts/detector-categories.md`: `aws_access_key_id`, `aws_secret_access_key`, `auth_token`, `access_token`, `refresh_token`, `session_token`, `passwd`, `pwd`, `bearer`, `auth`. Keep the existing keywords in the alternation. The regex shape stays `(?i)\b(<keywords>)\s*[:=]\s*([^\s"']+)`.
- [ ] T052 [US4] Extend the `vendor_token` detector's regex in `auditgraph/utils/redaction.py:_default_detectors()` to include the new GitHub prefixes (`github_pat_[A-Za-z0-9_]{20,}`, `gho_[A-Za-z0-9]{12,}`, `ghu_[A-Za-z0-9]{12,}`, `ghs_[A-Za-z0-9]{12,}`, `ghr_[A-Za-z0-9]{12,}`) and the new Slack format (`xoxe\.xoxp-[A-Za-z0-9-]{10,}`). Keep the existing `ghp_` and `xox[baprs]-` prefixes.
- [ ] T053 [US4] Add a NEW detector entry `"cloud_keys"` to `_default_detectors()` with `category="cloud_keys"` and a regex combining AWS (`AKIA[0-9A-Z]{16}`), Google (`AIza[0-9A-Za-z_-]{35}`), Anthropic (`sk-ant-api\d{2}-[A-Za-z0-9_-]{40,}`), OpenAI (`sk-proj-[A-Za-z0-9_-]{40,}|sk-[A-Za-z0-9]{48}`), and Stripe (`sk_live_[A-Za-z0-9]{24,}`). Use non-capturing groups where appropriate and the `re.X` verbose flag for readability.
- [ ] T054 [US4] Run Phase 6 tests (`pytest tests/test_spec027_cloud_keys_detectors.py tests/test_spec027_credential_kv_variants.py -v`) and confirm all ten green.
- [ ] T055 [US4] Run the existing `tests/test_redaction_detectors.py` to confirm the new detectors do not introduce false positives against the existing test corpus. If any existing test fails, investigate whether the failure is a legitimate regression or a fixture that contained a credential-shaped string that the new detectors are now catching.

**Checkpoint**: User Story 4 is independently complete. Demo via step 5 of `quickstart.md`.

---

## Phase 7: User Story 5 — Cross-chunk PEM keys are fully redacted (P2)

**Story goal**: Move redaction from post-chunking to parser-entry so full document text is scrubbed before chunking. The hotfix's post-chunking pass is retired in the same change. Multi-line secrets (PEM keys) are caught regardless of chunk size.

**Independent test**: Ingest a document with a 2048-bit RSA PEM key straddling a chunk boundary; walk every chunk file; assert no contiguous `[A-Za-z0-9+/=]` run longer than 40 characters survives.

### Tests for User Story 5

- [ ] T056 [US5] Write failing test `tests/test_spec027_cross_chunk_pem.py::test_cross_chunk_pem_redacted` that builds a document with a fake-but-realistic 2048-bit RSA PEM key (~1600 chars of base64 body) padded with 2000 tokens of filler prose on each side, writes it to `tmp_path/notes/`, runs `PipelineRunner().run_ingest(...)`, walks every `chunks/**/*.json` file, and asserts no chunk text contains a contiguous `[A-Za-z0-9+/=]` run longer than 40 characters (per research item R3).
- [ ] T057 [P] [US5] Write failing test `tests/test_spec027_cross_chunk_pem.py::test_in_chunk_pem_still_redacted` (the regression guard for FR-018) that ingests a short PEM key that fits entirely in one chunk and asserts the key is still redacted. Guards against the refactor accidentally removing the in-chunk case.
- [ ] T058 [P] [US5] Write failing test `tests/test_spec027_parser_redaction.py::test_redactor_is_threaded_into_parse_options` that constructs a `PipelineRunner`, enters `run_ingest`, and uses `unittest.mock.patch` on `parse_file` to capture the `parse_options` argument. Assert `"redactor" in parse_options` and the value is an instance of `Redactor`.
- [ ] T059 [P] [US5] Write failing test `tests/test_spec027_parser_redaction.py::test_hotfix_postchunking_pass_removed` that opens `auditgraph/pipeline/runner.py` as text, searches for occurrences of `redactor.redact_payload(document_payload)`, `redactor.redact_payload(segments_payload)`, `redactor.redact_payload(chunks_payload)` in the `run_ingest` and `run_import` functions, and asserts ZERO matches. This is a static check that the post-chunking pass has been retired. Use `inspect.getsource` or raw file read.
- [ ] T060 [P] [US5] Write failing test `tests/test_spec027_parser_redaction.py::test_parser_redacts_document_text` that calls `_build_document_metadata` directly with a text containing `password=TEST_SENTINEL`, passing a real `Redactor` via `parse_options`, and asserts the returned `document`, `segments`, and `chunks` payloads do NOT contain `TEST_SENTINEL` in any text field.

### Implementation for User Story 5

- [ ] T061 [US5] Modify `auditgraph/ingest/parsers.py:_build_document_metadata` (the entry point currently at ~line 91) to accept the `redactor` from `parse_options` and apply `text = redactor.redact_text(text).value` as the first line after extracting `text` from the parsed file. Every downstream reference to `text` — including `chunk_text(text, ...)` — then operates on already-redacted content.
- [ ] T062 [US5] Modify `auditgraph/ingest/parsers.py:parse_file` (and any other functions that call `_build_document_metadata`) to accept the `redactor` from `parse_options` and pass it through. If `parse_options` does not contain a redactor key, fall back to a no-op redactor to preserve behavior for test code paths that don't provide one.
- [ ] T063 [US5] Modify `auditgraph/pipeline/runner.py:run_ingest` to add `"redactor": redactor` to the `parse_options` dict constructed around line 146. The `redactor` variable is already built at line 135.
- [ ] T064 [US5] Modify `auditgraph/pipeline/runner.py:run_import` to build its own `redactor = build_redactor(root, config)` early in the function and add `"redactor": redactor` to its `parse_options` dict. The `run_import` function already builds a redactor post-hotfix; keep that unchanged and also thread it into parse_options.
- [ ] T065 [US5] **RETIRE** the hotfix's post-chunking redaction pass. Delete the `redacted_document = redactor.redact_payload(document_payload).value`, `redacted_segments = redactor.redact_payload(segments_payload).value`, `redacted_chunks = redactor.redact_payload(chunks_payload).value` lines and the corresponding `write_document_artifacts(..., redacted_document, redacted_segments, redacted_chunks)` call in BOTH `run_ingest` and `run_import`. Restore the simpler `write_document_artifacts(pkg_root, document_payload, segments_payload, chunks_payload)` call since the payloads are now pre-redacted by the parser. Keep the security comment but update it to point at parsers.py instead of describing a post-chunking defense.
- [ ] T066 [US5] Run the existing Phase 1 hotfix tests (`pytest tests/test_spec011_ingest_redaction.py -v`) and confirm all three tests still pass against the reorganized code path. The assertions (walk every shard, sentinel absent) are architecture-agnostic; they verify the behavior, not the code path.
- [ ] T067 [US5] Run Phase 7 tests (`pytest tests/test_spec027_cross_chunk_pem.py tests/test_spec027_parser_redaction.py -v`) and confirm all five green.

**Checkpoint**: User Story 5 is independently complete. The hotfix's post-chunking pass is retired. Demo via step 6 of `quickstart.md`.

---

## Phase 8: User Story 6 — Users can audit pre-hotfix `.pkg/` stores (P2)

**Story goal**: New `auditgraph validate-store` command that scans an existing `.pkg/` for credentials without a full rebuild. Active profile by default; `--profile` / `--all-profiles` override.

**Independent test**: Create a fixture `.pkg/` with a manually poisoned chunk; run `auditgraph validate-store`; confirm exit 1 and a report listing the poisoned shard path and detector category (without echoing the secret value).

### Tests for User Story 6

- [ ] T068 [US6] Write failing test `tests/test_spec027_validate_store.py::test_clean_store_exits_zero` that builds a clean fixture `.pkg/` via `PipelineRunner().run_ingest(...)` on a credential-free corpus, invokes the `validate_store` query function directly, and asserts the result status is `"pass"` with empty `misses` and exit-code translation is 0.
- [ ] T069 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_poisoned_store_exits_nonzero` that builds a clean store then mutates one chunk file on disk to inject `password=INJECTED_SENTINEL`, invokes `validate_store`, asserts status is `"fail"`, the `misses` list contains the chunk path with `category="credential"`, and the string `"INJECTED_SENTINEL"` does NOT appear anywhere in the result output.
- [ ] T070 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_no_pkg_exits_zero_with_message` that runs `validate_store` against a workspace with no `.pkg/` directory and asserts it returns status `"pass"` with a `"no store to validate"` message (not a crash).
- [ ] T071 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_profile_override` that builds two profiles (default and "dev"), poisons only the "dev" profile, runs `validate_store` with `--profile default`, asserts it returns pass; runs it again with `--profile dev`, asserts it returns fail.
- [ ] T072 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_all_profiles_flag` that creates the same two-profile fixture (default clean, dev poisoned), runs `validate_store` with `--all-profiles`, asserts the result has a `profiles` dict with entries for both profiles, `poisoned_profiles == ["dev"]`, and overall exit code is 1.
- [ ] T073 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_scope_excludes_runs_indexes_secrets` that poisons a file under `runs/` and under `indexes/` and under `secrets/`, runs `validate_store`, and asserts those files are NOT reported as misses (verifies FR-019 scope constraint per Clarification Q5).
- [ ] T074 [P] [US6] Write failing test `tests/test_spec027_validate_store.py::test_read_only_contract` that records the mtime of every file under `.pkg/profiles/default/` before running `validate_store`, runs it (on either a clean or poisoned store), and asserts no file's mtime has changed. Verifies FR-022.

### Implementation for User Story 6

- [ ] T075 [US6] Create `auditgraph/query/validate_store.py` with a `validate_store(pkg_root, *, profile=None, all_profiles=False) -> dict` function that (a) determines which profile(s) to scan, (b) walks `entities/`, `chunks/`, `segments/`, `documents/`, `sources/` under each selected profile, (c) reads each JSON file, (d) runs the detector set (via `build_redactor(...).redact_payload(...)` in detection-only mode — or directly iterates detectors against string fields) against every top-level string field, (e) records misses in the `{path, category, field}` shape, (f) returns a dict matching the `redaction_postcondition` shape from `data-model.md` with an additional `profile` or `profiles` wrapper.
- [ ] T076 [US6] Add a helper `_is_read_only_detector_scan(text, detectors) -> list[Match]` inside `validate_store.py` (or reuse the existing `Redactor._redact_text_with_summary` with a no-op substitution so it only reports, doesn't modify). The goal is a detection-only pass that produces the same category matches without mutating anything.
- [ ] T077 [US6] Modify `auditgraph/cli.py` to register a new `validate-store` subparser with `--root`, `--config`, `--profile`, `--all-profiles`, `--format` (choices: `json`, `text`) flags per `contracts/cli-commands.md`. Add a dispatch branch that calls `validate_store(...)` and formats the result based on `--format`.
- [ ] T078 [US6] Implement the text-format renderer in the dispatch branch: "No redaction misses detected." for clean runs; for dirty runs, list each miss as `<path> (<category> in field \`<field>\`)` grouped by profile when applicable. Exit codes: 0 for pass, 1 for fail.
- [ ] T079 [US6] Implement the JSON-format renderer in the dispatch branch that emits the same shape the `validate_store` function returns. Use `_emit(payload)` for stdout output consistency.
- [ ] T080 [US6] Add the `validate-store` command name to `auditgraph/utils/mcp_inventory.py:READ_TOOLS` so it can be exposed as a read-only MCP tool in a future spec iteration (not wired into the manifest in this spec unless a later task decides otherwise).
- [ ] T081 [US6] Run Phase 8 tests (`pytest tests/test_spec027_validate_store.py -v`) and confirm all seven green.

**Checkpoint**: User Story 6 is independently complete. Demo via step 7 of `quickstart.md`.

---

## Phase 9: User Story 7 — Remote Neo4j sync is warned about plaintext credentials (P3)

**Story goal**: Non-localhost `bolt://`/`neo4j://` URIs emit a stderr warning. `--require-tls` or `AUDITGRAPH_REQUIRE_TLS=1` escalates the warning to a refusal with exit code 4. Loopback hosts are exempt.

**Independent test**: `bolt://example.com` warns and connects; `bolt://example.com` with `--require-tls` refuses with exit 4; `bolt://localhost` does neither regardless of strict mode.

### Tests for User Story 7

- [ ] T082 [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_localhost_no_warning` that calls `load_profile_from_env()` with `NEO4J_URI=bolt://localhost:7687` and asserts no stderr warning is emitted. Capture stderr via `capsys` or `caplog`.
- [ ] T083 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_remote_plaintext_warns` with `NEO4J_URI=bolt://example.com:7687` that asserts a stderr line matching `WARN: Neo4j URI uses unencrypted scheme against non-localhost host example.com...` is emitted.
- [ ] T084 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_remote_tls_no_warning` with `NEO4J_URI=bolt+s://example.com:7687` asserting no warning.
- [ ] T085 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_require_tls_flag_refuses` that sets `NEO4J_URI=bolt://example.com:7687` and invokes the connection layer with `require_tls=True`, asserting a dedicated exception is raised (or the CLI exits with code 4). Verifies FR-023a CLI flag path.
- [ ] T086 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_require_tls_env_var_refuses` that sets `AUDITGRAPH_REQUIRE_TLS=1` in the environment and asserts the same refusal. Use `monkeypatch.setenv` to set the variable without leaking into other tests.
- [ ] T087 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_localhost_require_tls_still_allowed` with `bolt://localhost:7687` AND `--require-tls` asserting no refusal (loopback exempts even under strict mode).
- [ ] T088 [P] [US7] Write failing test `tests/test_spec027_neo4j_plaintext_warning.py::test_ipv6_localhost_recognized` with `bolt://[::1]:7687` asserting no warning emitted. Also test `bolt://127.0.0.1:7687` for completeness.

### Implementation for User Story 7

- [ ] T089 [US7] Modify `auditgraph/neo4j/connection.py:load_profile_from_env` (or the connection-construction code path — plan phase identifies the exact function) to parse the URI host, check if it is in `{"localhost", "127.0.0.1", "::1"}`, and if NOT, check the scheme. If the scheme is `bolt://` or `neo4j://` (unencrypted), emit the stderr warning.
- [ ] T090 [US7] Add a `_is_loopback_host(host: str) -> bool` helper in `auditgraph/neo4j/connection.py` that canonicalizes the host (strips port, strips IPv6 brackets, lowercases) and returns True for `{"localhost", "127.0.0.1", "::1"}`. Unit-test this helper as part of T082-T088.
- [ ] T091 [US7] Add a `require_tls` parameter to `load_profile_from_env` (or the equivalent construction function) that when True promotes the warning to a raised exception with a dedicated error class (`Neo4jTlsRequiredError` or reuse `PathPolicyError`-style). Honor `AUDITGRAPH_REQUIRE_TLS=1` env var as equivalent — check `os.environ.get("AUDITGRAPH_REQUIRE_TLS") == "1"` in the same function.
- [ ] T092 [US7] Modify `auditgraph/cli.py` to add `--require-tls` flag to the `sync-neo4j` and `export-neo4j` subparsers. In the dispatch branches, catch `Neo4jTlsRequiredError` and exit with code 4 after emitting an `ERROR:` line to stderr.
- [ ] T093 [US7] Run Phase 9 tests (`pytest tests/test_spec027_neo4j_plaintext_warning.py -v`) and confirm all seven green.

**Checkpoint**: User Story 7 is independently complete. Demo via step 8 of `quickstart.md`.

---

## Phase 10: User Story 8 — Pipeline postcondition prevents redaction regressions (P3)

**Story goal**: After the `index` stage completes, walk every shard directory and re-run the detector set. On match, fail the rebuild with exit code 3 unless `--allow-redaction-misses` was passed (then `status: "tolerated"` and exit 0).

**Independent test**: Mutate a chunk file on disk after a clean rebuild; run the postcondition directly; assert it reports the mutation with status `"fail"`.

### Tests for User Story 8

- [ ] T094 [US8] Write failing test `tests/test_spec027_postcondition.py::test_clean_rebuild_status_pass` that runs `PipelineRunner().run_stage("rebuild", ...)` on a clean workspace and asserts the final manifest contains `redaction_postcondition.status == "pass"`, `misses == []`, `allow_misses == false`.
- [ ] T095 [P] [US8] Write failing test `tests/test_spec027_postcondition.py::test_dirty_rebuild_status_fail_exit_3` that runs a clean rebuild, mutates a chunk file to inject `password=SENTINEL`, then re-runs only the postcondition function (not the full rebuild) on the mutated store, asserts it returns `status == "fail"`, and that invoking the `rebuild` CLI command on this mutated state would exit with code 3. Mock the CLI dispatch if running the full command is impractical in a unit test.
- [ ] T096 [P] [US8] Write failing test `tests/test_spec027_postcondition.py::test_allow_misses_flag_tolerates` that runs the same mutation scenario with `--allow-redaction-misses` and asserts `status == "tolerated"`, `allow_misses == true`, exit code 0.
- [ ] T097 [P] [US8] Write failing test `tests/test_spec027_postcondition.py::test_postcondition_scope_same_as_validate_store` verifying the postcondition walks `entities/chunks/segments/documents/sources` (same scope as `validate-store`) and skips `runs/indexes/secrets`.
- [ ] T098 [P] [US8] Write failing test `tests/test_spec027_postcondition.py::test_postcondition_wallclock_budget` that runs the postcondition on a 100-file test corpus and asserts `wallclock_ms < 2000` (generous ceiling; real SC-008 budget is ≤ 100% of baseline rebuild, which on a 100-file corpus is much faster).
- [ ] T099 [P] [US8] Write failing test `tests/test_spec027_postcondition_manifest.py::test_manifest_entry_shape_pass` that runs a clean rebuild and asserts the manifest JSON contains the exact `redaction_postcondition` field shape from `contracts/postcondition-manifest.md`: `status`, `misses`, `allow_misses`, `scanned_shards`, `wallclock_ms` keys; `status` is one of the four enum values; `misses` is a list; etc.
- [ ] T100 [P] [US8] Write failing test `tests/test_spec027_postcondition_manifest.py::test_miss_sub_shape` that runs the dirty scenario and asserts every entry in `misses` has `path`, `category`, `field` keys (and only those keys), and that the matched secret value does NOT appear anywhere in the manifest JSON.
- [ ] T101 [P] [US8] Write failing test `tests/test_spec027_postcondition_manifest.py::test_misses_sorted_deterministically` that injects misses into multiple shards and asserts the `misses` array is sorted by `(path, field, category)` as required by the contract.
- [ ] T102 [P] [US8] Write failing test `tests/test_spec027_postcondition_manifest.py::test_skipped_status_on_prior_stage_failure` that simulates a prior-stage failure (e.g., mock `run_extract` to raise) and asserts the final manifest has `redaction_postcondition.status == "skipped"`.

### Implementation for User Story 8

- [ ] T103 [US8] Create `auditgraph/pipeline/postcondition.py` with a `run_postcondition(pkg_root, profile, *, allow_misses=False) -> PostconditionResult` function that (a) builds the same detector set the ingest pipeline uses, (b) walks `entities/chunks/segments/documents/sources` under the active profile, (c) scans each JSON for detector matches in string fields, (d) records misses, (e) returns a dataclass/dict with the `status`, `misses`, `allow_misses`, `scanned_shards`, `wallclock_ms` fields.
- [ ] T104 [US8] The postcondition's walk and detection logic is substantially similar to `validate_store.py` from Phase 8. Extract the shared logic into a helper module `auditgraph/query/_shard_scanner.py` or similar so the two callers don't duplicate (DRY per Constitution I). Both `postcondition.py` and `validate_store.py` import and use the helper.
- [ ] T105 [US8] Modify `auditgraph/pipeline/runner.py:run_rebuild` (or whichever function the rebuild stage uses) to call `run_postcondition(pkg_root, profile, allow_misses=allow_redaction_misses)` as the final step after `run_index` completes. Merge the returned `redaction_postcondition` field into the final stage manifest. On `status == "fail"`, raise a dedicated exception that the CLI dispatch catches to emit exit code 3. On `status == "tolerated"`, log but do not raise.
- [ ] T106 [US8] Modify `auditgraph/cli.py` to add `--allow-redaction-misses` flag to the `rebuild` subparser. In the dispatch branch, pass the flag value through to the runner. On the dedicated "postcondition failed" exception, emit an `ERROR:` line to stderr and `sys.exit(3)`.
- [ ] T107 [US8] Ensure the "prior-stage failure" path still emits a `redaction_postcondition` entry with `status: "skipped"` in the manifest (even if rebuild short-circuits). This requires a try/finally pattern in `run_rebuild` so the manifest is written with the skipped entry on any pre-postcondition exception.
- [ ] T108 [US8] Run Phase 10 tests (`pytest tests/test_spec027_postcondition.py tests/test_spec027_postcondition_manifest.py -v`) and confirm all nine green.
- [ ] T109 [US8] Run the full test suite (`pytest tests/ -q`) and confirm the new postcondition does not cause regressions in other tests. In particular, any test that runs a full `rebuild` must still pass, because the postcondition will now run at the end of those tests too.

**Checkpoint**: User Story 8 is independently complete. Pipeline redaction is self-enforcing. Demo via step 9 of `quickstart.md`.

---

## Phase 11: Polish & Cross-Cutting Concerns

After all user stories are individually green, the final phase bundles documentation, changelog, and re-audit tasks. No production code is written here except doc updates.

- [ ] T110 Update `CHANGELOG.md` with a `## Unreleased` entry under `### Security` (matching the Phase 1 format) that summarizes Spec 027: symlink containment, MCP validation, export-neo4j path fix, detector expansion, cross-chunk PEM fix (and the retirement of the hotfix's post-chunking pass), `validate-store` command, Neo4j plaintext warning, pipeline postcondition. Include migration guidance for users with pre-Phase-1 stores: run `auditgraph validate-store` and if poisoned, run `auditgraph rebuild`.
- [ ] T111 Update `README.md` CLI Reference section to add `validate-store` and the new flags. Update the "Feature Status" table if any row labels change (no new rows expected).
- [ ] T112 Update `QUICKSTART.md` if the first-success walkthrough touches any of the modified commands. Smoke-check that the documented invocations still work.
- [ ] T113 [P] Update `CLAUDE.md` Common Pitfalls section with any new gotchas discovered during implementation (e.g., `--allow-redaction-misses` naming, the postcondition's scope exclusions, the `--require-tls` env var equivalent).
- [ ] T114 [P] Regenerate MCP artifacts if the manifest was modified in T033/T034: `python llm-tooling/generate_skill_doc.py && python llm-tooling/generate_adapters.py`. Re-run `pytest llm-tooling/tests -q` to confirm contract tests pass.
- [ ] T115 Run the full test suite one final time (`pytest tests/ -q`) and confirm (a) all 805+ existing tests plus the ~60 new Spec 027 tests pass, (b) total wallclock is under 60 seconds (SC-009), (c) no flaky failures on a second run.
- [ ] T116 Re-run the aegis deep audit against the Phase 2-4 scope areas (symlinks, MCP contract, export paths, redaction coverage, pipeline postcondition). Expected outcome per SC-010: zero HIGH or CRITICAL findings remaining in those categories. Document any residual findings in a new `specs/028-*` NOTES file; do not silently close them.
- [ ] T117 Commit the work on branch `027-security-hardening`. Multiple commits are acceptable (one per user story is clean and aligns with Constitution IV) but the entire spec must ship in one PR so the quickstart walkthrough works end-to-end. Do NOT add `Co-Authored-By: Claude` trailers (project-specific rule).
- [ ] T118 Open the PR against `main`. Title format: `feat(security): Spec 027 hardening Phases 2-4`. Body cross-references `specs/026-security-hardening/NOTES.md` for the audit context and the Phase 1 hotfix commit (`215398d`) for the history of how we got here.

---

## Dependencies

**Setup phase (T001-T004)** blocks everything. T001+T002 must complete before T003 (install); T003 must complete before T004 (which imports from the installed `jsonschema`).

**Foundational phase (T005-T010)** blocks user stories as follows:
- T005-T006 (`SKIP_REASON_SYMLINK_REFUSED` constant) blocks Phase 3 (US1).
- T007-T008 (`contained_symlink_target` helper) blocks Phase 3 (US1).
- T009-T010 (`mcp/validation.py` skeleton) blocks Phase 4 (US2).

**User story phases are mostly independent of each other** — they can be parallelized across developers or AI agents. The dependencies are:
- **Phase 7 (US5 cross-chunk PEM) MUST land before or together with Phase 10 (US8 postcondition)**. The postcondition tests assume the parser-entry redaction is in place; running US8 against the hotfix's post-chunking redaction would produce confusing failures.
- **Phase 8 (US6 validate-store) and Phase 10 (US8 postcondition) share a helper** (`_shard_scanner.py` from T104). Whichever phase lands second must extract the shared helper rather than duplicate. If Phase 10 lands first, T104 moves forward; if Phase 8 lands first, T075 creates `_shard_scanner.py` from the start and T104 becomes a no-op "confirm reuse" task.

**Phase 11 (Polish)** blocks on all user stories being green.

### User story priority order for MVP delivery

If time is constrained, ship in this order (higher priority first):
1. **Phase 3 (US1 symlink containment)** — P1, closes the only remaining HIGH finding that an LLM cannot mitigate from outside the pipeline.
2. **Phase 4 (US2 MCP validation)** — P1, closes the MCP trust boundary.
3. **Phase 7 (US5 cross-chunk PEM)** — P2 but architecturally load-bearing (retires the hotfix pass).
4. **Phase 5 (US3 export-neo4j path)** — P2, small and easy.
5. **Phase 6 (US4 detector expansion)** — P2, independent of all other phases.
6. **Phase 8 (US6 validate-store)** — P2, builds on US4 for detector coverage.
7. **Phase 10 (US8 postcondition)** — P3, defense in depth; shares helper with US6.
8. **Phase 9 (US7 Neo4j warning)** — P3, lowest impact, can ship last.

**MVP scope**: Phases 1-4 (setup + foundational + US1 + US2) close both P1 findings and deliver the most critical security value. Everything else can land in a subsequent PR if needed. Spec 027 is written to ship the whole scope in one PR, but the MVP boundary exists as a fallback if any single phase takes longer than expected.

### Parallel execution opportunities

Within each user story phase, test tasks marked `[P]` are independent and can run in parallel (different test files or independent test functions in the same file). Within the implementation tasks of a single user story, sequential ordering is recommended unless explicitly marked `[P]`.

Across phases, Phases 3, 4, 5, 6, 8, 9 are mutually independent in terms of file modifications and can be worked on in parallel by multiple agents or developers. Phases 7 and 10 touch shared code paths (`pipeline/runner.py`) and should be serialized. Phase 11 waits for everything else.

---

## Task count summary

| Phase | Tasks | Description |
|---|---|---|
| 1 — Setup | 4 | Dependency baseline: `jsonschema` + parser pins |
| 2 — Foundational | 6 | Shared helpers: skip reason, `contained_symlink_target`, validation module skeleton |
| 3 — US1 Symlink containment (P1) | 12 | Tests + scanner/importer/runner/cli changes |
| 4 — US2 MCP validation (P1) | 13 | Tests + validator impl + server wiring + manifest updates |
| 5 — US3 Export-neo4j path (P2) | 5 | Tests + cli dispatch fix |
| 6 — US4 Detector expansion (P2) | 15 | Tests for each format + cloud_keys + credential_kv + vendor_token updates |
| 7 — US5 Cross-chunk PEM / parser redaction (P2) | 12 | Tests + parser redaction + retirement of hotfix pass |
| 8 — US6 Validate-store command (P2) | 14 | Tests + validate_store module + CLI integration + shard-scanner helper |
| 9 — US7 Neo4j plaintext warning (P3) | 12 | Tests + connection.py warning + refusal + CLI flag |
| 10 — US8 Pipeline postcondition (P3) | 16 | Tests + postcondition module + runner integration + manifest shape |
| 11 — Polish | 9 | Docs, changelog, MCP regen, full-suite + re-audit, commit + PR |
| **Total** | **118** | |

## Format validation

Every task above is verified to follow the required format:
- Starts with `- [ ]` checkbox
- Task ID `T001` through `T118` sequential
- `[P]` marker present where task is parallelizable
- `[Story]` label (`[US1]` through `[US8]`) present on every user story task; absent on Setup, Foundational, and Polish tasks
- File paths included in descriptions where applicable (e.g., `auditgraph/ingest/scanner.py`, `tests/test_spec027_symlink_containment.py`)

Ready for `/speckit.analyze` followed by `/speckit.implement`.
