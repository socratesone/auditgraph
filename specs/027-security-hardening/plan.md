# Implementation Plan: Security Hardening (Phases 2-4)

**Branch**: `027-security-hardening` | **Date**: 2026-04-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/027-security-hardening/spec.md`

## Summary

Harden the auditgraph ingest, MCP, export, and Neo4j code paths by closing the six remaining findings from the post-Spec-025 security audit and adding three defense-in-depth deliverables. The work is decomposed into eight user stories with 30 functional requirements and 10 measurable success criteria; all eight original ambiguities have been resolved through two clarify sessions and recorded in the spec's Clarifications block.

**Technical approach at a glance.** The redactor gains a new parser-entry integration point (`_build_document_metadata` receives a `redactor` in `parse_options` and scrubs raw text before chunking, which also retires the hotfix's post-chunking pass). The MCP server gains a `jsonschema`-backed validation layer between transport and argv construction. The ingest walker gains a per-path symlink containment check. The `export-neo4j` CLI handler gains the same `ensure_within_base` check that `export` already uses. A new `auditgraph validate-store` command is added for auditing pre-hotfix stores. A new pipeline postcondition (`auditgraph/pipeline/postcondition.py`) walks shard directories and re-runs the detector set as the final rebuild step, failing the run with exit code 3 on any miss unless `--allow-redaction-misses` is passed. The Neo4j connection layer emits a stderr warning for non-localhost plaintext URIs, with a `--require-tls` / `AUDITGRAPH_REQUIRE_TLS=1` opt-in refusal. `pyproject.toml` gains lower bounds for the three untrusted-input parsers (`pyyaml`, `pypdf`, `python-docx`) plus the new `jsonschema>=4,<5` dependency.

Every deliverable is test-first: each new regex, CLI command, or postcondition branch ships with a failing test written before the implementation, per Constitution Principle III.

## Technical Context

**Language/Version**: Python 3.10+ (unchanged from current project baseline; no new version requirement)
**Primary Dependencies**: argparse (stdlib), PyYAML, pypdf, python-docx, dulwich, optional spaCy, optional neo4j driver. **NEW**: `jsonschema>=4,<5` (pure Python, ~200 KB, zero compiled deps). **PINNED** (lower bound only, no upper bound unless an incompatibility is discovered): `pyyaml`, `pypdf`, `python-docx`.
**Storage**: Sharded JSON files under `.pkg/profiles/<profile>/` (unchanged). No new shard types, no new index files, no new schema version. The run manifest gains one new structured field (`redaction_postcondition`); otherwise the on-disk layout is untouched.
**Testing**: pytest with `--strict-markers` (unchanged). Test organization stays spec-based (`tests/test_spec027_*.py`) matching auditgraph convention. Roughly 12 new test files estimated, each covering one user story or a named sub-area (detectors, symlink walker, MCP validator, postcondition, validate-store command, Neo4j warning).
**Target Platform**: Linux (primary), macOS (supported). No platform-specific code is introduced by this spec — all symlink, path, and process handling uses stdlib `pathlib` and `subprocess` which work uniformly.
**Project Type**: Single Python package (unchanged). No new top-level directories; all additions go under `auditgraph/` and `tests/` (and `llm-tooling/mcp/` for the MCP validator). One new module under `auditgraph/pipeline/` (`postcondition.py`), one new module under `auditgraph/query/` (`validate_store.py`), and one new module under `llm-tooling/mcp/` (`validation.py`).
**Performance Goals**:
- Pipeline postcondition MUST NOT more than double the end-to-end rebuild wallclock (FR-028, SC-008).
- Full repository test suite MUST run under 60 seconds on the reference developer machine after the new test files land (SC-009; today's baseline is 27.5 seconds post-Phase-1).
- MCP validation adds at most a few milliseconds per tool call (jsonschema Draft 7 validation of a flat object with ~5 properties is effectively free).
**Constraints**:
- Determinism: every new code path must produce identical output for identical input (Constitution V). Detector regex order matters for reproducible summaries.
- Local-first: no network calls from core pipeline. `jsonschema` is pure offline; Neo4j remains an optional outbound target (unchanged).
- Backwards compatibility: new CLI flags are additive (`--require-tls`, `--allow-redaction-misses`, `--profile`, `--all-profiles`, `--allow-symlinks`). No existing invocation changes behavior except the new stderr warnings (symlink refusal summary, Neo4j plaintext warning) which do not alter exit codes in their default modes.
- No co-author trailers on commits (project-specific rule in CLAUDE.md).
- M2 must be closed by moving redaction into the parser entry point (Clarification Q1); the hotfix's post-chunking redaction is retired in the same change.
**Scale/Scope**:
- 30 functional requirements (FR-001 through FR-030)
- 10 success criteria (SC-001 through SC-010)
- 8 user stories across 3 priority tiers (2 × P1, 4 × P2, 2 × P3)
- Estimated ~600-900 lines of production code across 6-8 modified files + 3 new modules
- Estimated ~1200-1800 lines of test code across ~12 new test files
- 1 new CLI subcommand (`validate-store`), 5 new CLI flags, 1 new env var, 1 new runtime dependency

## Constitution Check

**Gate status**: PASS (evaluated against `.specify/memory/constitution.md` Version 1.0.0).

### I. DRY — Single Source of Truth

| Requirement | Status | Notes |
|---|---|---|
| No duplicated logic across symlink check, redactor, validator | PASS | Symlink containment reuses existing `ensure_within_base` (`utils/paths.py`). Redactor is a single `Redactor` instance threaded through `parse_options`, replacing the hotfix's double-redaction structure (which is removed, net DRY improvement). MCP validator is one module in `llm-tooling/mcp/validation.py` used by both stdio and any future transport. |
| Detector patterns live in one place | PASS | `cloud_keys` and `vendor_token` both live in `auditgraph/utils/redaction.py:_default_detectors()`. |
| Postcondition reuses the ingest-time detector set | PASS | `auditgraph/pipeline/postcondition.py` imports `build_redactor` and reuses the exact same detector configuration the ingest pipeline used, so a miss in the postcondition can only mean a genuine bypass, not a detector mismatch. |

**DRY improvements delivered by this spec**:
- Retires the hotfix's post-chunking redaction pass (eliminates duplicated redaction work between `run_ingest` and `run_import`).
- Consolidates per-path containment checks into a single helper that both scanner and importer call.

### II. SOLID Architecture

| Principle | Status | Notes |
|---|---|---|
| Single Responsibility | PASS | New modules are narrowly scoped: `postcondition.py` walks shards and reports misses (nothing else); `mcp/validation.py` validates payloads against schemas (nothing else); `query/validate_store.py` implements one read-only audit operation (nothing else). Existing modules that grow (`parsers.py`, `redaction.py`) gain focused additions, not grab-bag changes. |
| Open/Closed | PASS | The detector registry in `_default_detectors()` is already open for extension — new detectors are added by returning additional entries from the factory. Phase 2 adds entries, does not modify existing ones (except `vendor_token`, which extends its regex alternation to cover new GitHub prefixes per FR-014). |
| Liskov Substitution | N/A | No new class hierarchies introduced. |
| Interface Segregation | PASS | The new MCP validator exposes a single `validate(tool_schema, payload) -> ValidationResult` function. No fat interfaces. |
| Dependency Inversion | PASS | `jsonschema` is pulled behind a thin adapter in `mcp/validation.py` so swapping validators later (if the library becomes a problem) only touches that one file. The `Redactor` continues to be injected into the parser via `parse_options` rather than constructed there — consistent with DI. |

### III. Test-Driven Development (NON-NEGOTIABLE)

Every functional requirement in the spec has a corresponding failing-first test acceptance scenario. Plan enforces TDD by ordering tasks as: (1) write failing test for the story's Independent Test, (2) implement minimal code to pass, (3) refactor, (4) add edge case tests from the spec's Edge Cases section, (5) verify the postcondition catches a manually-injected miss. No production code is written in Phase 2 until the corresponding failing test exists.

### IV. Refactoring as First-Class Activity

The plan explicitly retires the hotfix's post-chunking redaction pass (a refactor, not an addition) as part of User Story 5 implementation. It also consolidates symlink containment into a single helper shared by scanner and importer (a refactor, not an addition). Both refactors ship in the same PRs as their corresponding feature additions, so no "I'll clean it up later" debt accumulates.

### V. Simplicity and Determinism

- YAGNI applied: `--allow-symlinks` flag is reserved but not implemented (Clarification Q3). No speculative abstractions for future multi-line secret types beyond what the parser-entry redaction gives for free.
- All new code paths are deterministic: regex detectors produce the same matches for the same input, path containment uses `resolve()` consistently, postcondition walks shards in sorted order, MCP validator produces stable error messages.
- No hidden side effects: the postcondition is a read-only walk; `validate-store` is strictly read-only per FR-022; the Neo4j warning writes only to stderr.

### Quality Gates (from constitution)

| Gate | Strategy |
|---|---|
| All tests pass (unit + integration) | Full suite runs before each phase-complete commit; CI expected to run `pytest -q` on push. |
| Coverage exists for all business rules | Each FR maps to ≥1 test (see data-model.md and the task decomposition that `/speckit.tasks` will produce). |
| No duplicated logic detected | Symlink containment helper shared between scanner and importer; detector registry extended via factory, not copy-pasted. |
| SOLID violations addressed or justified | None introduced by this spec. Existing `PipelineRunner` god-class (885 lines) is explicitly out of scope per spec Assumptions; this spec does not make it worse. |
| Public APIs documented | New CLI flags and `validate-store` command go into README.md CLI Reference and CLAUDE.md project map. Postcondition manifest schema is documented in quickstart.md and `contracts/postcondition-manifest.md`. |
| Static analysis: zero high-severity findings | Post-implementation, re-run aegis audit against the categories in scope (SC-010). |

**Result**: All constitution gates PASS. No complexity tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/027-security-hardening/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   ├── cli-commands.md              # CLI surface changes (new flags, new command)
│   ├── mcp-validation-errors.md     # Structured error shape for MCP validation failures
│   ├── postcondition-manifest.md    # New redaction_postcondition manifest field schema
│   └── detector-categories.md       # cloud_keys vs vendor_token category contract
├── checklists/
│   └── requirements.md              # (already created by /speckit.specify)
└── tasks.md                         # Phase 2 output (/speckit.tasks, NOT created here)
```

### Source Code (repository root)

Additions and modifications are listed. Files not mentioned are untouched by this spec.

```text
auditgraph/
├── cli.py                            # MODIFIED: add --require-tls, --allow-redaction-misses,
│                                     #   --profile/--all-profiles, --allow-symlinks flags;
│                                     #   wire `validate-store` subcommand; add ensure_within_base
│                                     #   check to export-neo4j handler (mirroring export)
├── ingest/
│   ├── scanner.py                    # MODIFIED: per-path symlink containment check,
│   │                                 #   emit symlink_refused skip reason
│   ├── importer.py                   # MODIFIED: same per-path containment check
│   ├── parsers.py                    # MODIFIED: thread redactor into _build_document_metadata,
│   │                                 #   redact full document text before chunking
│   └── policy.py                     # MODIFIED: add SKIP_REASON_SYMLINK_REFUSED constant
├── pipeline/
│   ├── runner.py                     # MODIFIED: pass redactor into parse_options for run_ingest
│   │                                 #   and run_import; remove hotfix's post-chunking redaction
│   │                                 #   pass; invoke postcondition at end of run_rebuild
│   └── postcondition.py              # NEW: walk shards, re-run detectors, emit manifest entry
├── query/
│   └── validate_store.py             # NEW: read-only shard walk + detector scan for the
│                                     #   `auditgraph validate-store` command
├── neo4j/
│   └── connection.py                 # MODIFIED: non-localhost plaintext warning + --require-tls
│                                     #   refusal; honor AUDITGRAPH_REQUIRE_TLS env var
├── utils/
│   ├── redaction.py                  # MODIFIED: add cloud_keys detector category; extend
│   │                                 #   credential_kv keyword list; extend vendor_token for
│   │                                 #   new GitHub prefixes
│   └── paths.py                      # MODIFIED: add contained_symlink_target(path, base)
│                                     #   helper used by scanner and importer

llm-tooling/
├── mcp/
│   ├── server.py                     # MODIFIED: call validate(payload, tool_schema) before
│   │                                 #   build_command; translate ValidationError to
│   │                                 #   structured error shape
│   └── validation.py                 # NEW: jsonschema-backed payload validator with size caps
└── tool.manifest.json                # MODIFIED: add maxLength to string parameters that
                                      #   don't already have one (server-default fallback
                                      #   still applies for parameters without explicit caps)

config/
└── pkg.yaml                          # UNCHANGED: no config schema additions; all new behavior
                                      #   is CLI-flag or env-var driven

pyproject.toml                         # MODIFIED: add jsonschema>=4,<5; add lower bounds for
                                      #   pyyaml, pypdf, python-docx at post-Phase-1 audit baseline

tests/
├── test_spec027_symlink_containment.py     # NEW: User Story 1 — ingest+import symlink refuse
├── test_spec027_mcp_payload_validation.py  # NEW: User Story 2 — schema-driven payload validation
├── test_spec027_export_neo4j_containment.py # NEW: User Story 3 — export-neo4j path containment
├── test_spec027_cloud_keys_detectors.py    # NEW: User Story 4 — cloud_keys detector matches
├── test_spec027_credential_kv_variants.py  # NEW: User Story 4 — expanded key=value keywords
├── test_spec027_cross_chunk_pem.py         # NEW: User Story 5 — cross-chunk PEM redaction
├── test_spec027_parser_redaction.py        # NEW: User Story 5 — parser-entry redaction wiring
├── test_spec027_validate_store.py          # NEW: User Story 6 — validate-store command
├── test_spec027_neo4j_plaintext_warning.py # NEW: User Story 7 — bolt:// warning + --require-tls
├── test_spec027_postcondition.py           # NEW: User Story 8 — rebuild postcondition behavior
├── test_spec027_postcondition_manifest.py  # NEW: User Story 8 — manifest entry shape
└── test_spec027_dependency_baseline.py     # NEW: FR-029/030 — pyproject.toml pins exist
                                            #   (metadata test, not runtime behavior)
```

**Structure Decision**: Single Python package (existing auditgraph layout). No new top-level directories. New modules go under `auditgraph/pipeline/` (postcondition), `auditgraph/query/` (validate-store), and `llm-tooling/mcp/` (validator) to match the existing convention of "behavior lives next to its peers". Tests use the established `test_spec<NNN>_<topic>.py` naming, one file per user story plus supporting sub-area files where a story's test surface is too large for a single file.

## Complexity Tracking

Not applicable. All constitution gates pass on the first evaluation; no violations require justification. The spec is scoped to avoid the one open structural concern (`PipelineRunner` god-class) so this plan does not accumulate complexity debt while it lands.

---

## Phase 0: Outline & Research

**Prerequisite:** Spec fully clarified (8 of 8 open questions resolved in Clarifications section).

### Unknowns in Technical Context

All Technical Context fields are resolved. There are no `NEEDS CLARIFICATION` markers. The only items that would normally drive research are:

1. **Exact lower-bound versions for `pyyaml`, `pypdf`, `python-docx`** — pinned to "post-Spec-025 audit baseline" in FR-029 but not yet expressed as concrete version strings. Resolved by querying the current venv's installed versions and the latest stable releases, documented in research.md.
2. **The specific list of Neo4j URI schemes considered "unencrypted"** — `bolt://` and `neo4j://` are obvious, but what about `bolt+routing://` (deprecated, not in the current allowlist)? Resolved by reading the current allowlist in `neo4j/connection.py:30` and matching Neo4j's own documentation.
3. **The safe base64 run length for the cross-chunk PEM regression test** — SC-005 says "longer than 40 characters" without justification. Resolved by checking whether 40 characters of base64 is enough to distinguish a key body from legitimate content like SHA hashes (64 chars), UUIDs (32 chars, non-base64), and citation tokens.
4. **Whether jsonschema's default Draft 7 validator covers the manifest's existing syntax** — need to confirm `additionalProperties: false`, `maxLength`, `minimum`/`maximum`, `enum`, `required` all validate as expected. Resolved by reading the jsonschema library's draft compatibility matrix.
5. **Whether the existing `ensure_within_base` helper correctly handles a resolved symlink target** — it does path-prefix checking, but we need to confirm it resolves both sides. Resolved by reading `auditgraph/utils/paths.py` and adding a regression test.

These are all quick lookups rather than multi-agent research tasks. They are consolidated in **research.md** as a five-entry decision log.

## Phase 1: Design & Contracts

**Prerequisite:** research.md complete.

### Data model

The spec introduces no new entities in the auditgraph sense (no new shard type, no new entity label). What it does introduce:

1. A new structured manifest entry (`redaction_postcondition`) appended to the `rebuild` run manifest.
2. A new skip reason (`symlink_refused`) added to the existing ingest-manifest vocabulary.
3. A new detector category (`cloud_keys`) alongside the existing categories in the redaction summary schema.
4. A new MCP validation error shape.

These are documented in **data-model.md** as field definitions with types, defaults, and example values.

### Contracts

Four contract documents live in `contracts/`:

1. **`cli-commands.md`** — exact flag list, help text, exit codes, and stderr behavior for every new/modified CLI command: `ingest`, `import`, `rebuild`, `export-neo4j`, `sync-neo4j`, `validate-store`.
2. **`mcp-validation-errors.md`** — the structured error envelope returned by `execute_tool` on validation failure, and the specific `jsonschema.ValidationError` → project error translation rules.
3. **`postcondition-manifest.md`** — the `redaction_postcondition` field schema, possible status values (`pass`/`fail`/`tolerated`/`skipped`), and the per-miss record shape.
4. **`detector-categories.md`** — the reporting-category contract for `cloud_keys` vs `vendor_token`, including which prefixes belong to which category and how summary reports present them.

### Quickstart

`quickstart.md` contains a linear walkthrough:
1. Create a hostile-workspace fixture with an escaping symlink.
2. Run `auditgraph ingest` and confirm the stderr warning + manifest skip reason.
3. Run `auditgraph validate-store` against a pre-Phase-1 poisoned store fixture.
4. Run `auditgraph rebuild --allow-redaction-misses` and confirm the tolerated-miss path.
5. Run `auditgraph sync-neo4j --require-tls` against `bolt://example.com` and confirm refusal.
6. Submit an unknown-key MCP payload and confirm rejection before subprocess invocation.

This doubles as the acceptance test narrative — each step maps to one user story and one test file.

### Agent context update

Phase 1 will run `.specify/scripts/bash/update-agent-context.sh claude` to refresh `CLAUDE.md` with the new technology and conventions: the `jsonschema` dependency, the new `postcondition.py` module, the new `validate-store` command, and the new CLI flags. This update is idempotent and preserves manual additions between the existing agent-context markers.

### Post-Phase-1 Constitution re-check

Re-evaluate Constitution Check after the contracts and data-model are written to verify that no design decision has introduced a violation that was not visible during the initial check. Expected result: PASS (same as pre-Phase-1), since the design follows the same shape as existing auditgraph patterns.

---

## Ready for `/speckit.tasks`

After this plan is committed:
1. `research.md` resolves the five research items documented in Phase 0.
2. `data-model.md` formalizes the four new data shapes.
3. `contracts/*.md` (four files) nail down the external interface surface.
4. `quickstart.md` gives the acceptance-test narrative.
5. `update-agent-context.sh` refreshes `CLAUDE.md`.

Then `/speckit.tasks` can decompose User Stories 1-8 into sequenced implementation tasks with the failing-first TDD ordering the constitution requires.
