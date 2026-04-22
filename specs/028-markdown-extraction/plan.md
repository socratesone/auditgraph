# Implementation Plan: Markdown ingestion produces honest, queryable results

**Branch**: `028-markdown-extraction` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/028-markdown-extraction/spec.md`

## Summary

Make markdown ingestion produce queryable, structured results across repeated runs. Six user stories are bundled into one spec because they share one corpus fixture and one end-to-end journey: **a user points `auditgraph` at a markdown corpus and ends up with honest, navigable, queryable output.** The implementation splits into four small surgical fixes (BUG-1/2/4/5 + BUG-3 polish) plus one new producer module:

- **US1 (BUG-1)** — separate "parse outcome" from "execution origin" in the ingest record shape. Cached files get `parse_status="ok"` + `source_origin="cached"`; extract reads on `parse_status` alone. Backward-compatible reader translates the legacy `parse_status="skipped" + skip_reason="unchanged_source_hash"` shape.
- **US2 (Spec-028 proper)** — new `auditgraph/extract/markdown.py` module uses `markdown-it-py` (already a transitive dep of `rich`) to walk markdown tokens, emitting `ag:section` / `ag:technology` / `ag:reference` entities and four link types: `contains_section`, `mentions_technology`, `references` (section → reference, always), and `resolves_to_document` (reference → doc, internal-only). Deterministic IDs via existing `sha256_*` helpers, with source-scoped hash inputs per `data-model.md §1.0`. Redaction via the Spec-027 canonical redactor. Internal-reference classification uses the `documents/` store populated in the same run.
- **US3 (BUG-5)** — `StageManifest.warnings` field; `run_extract` / `run_index` emit structured `no_entities_produced` / `empty_index` warnings when throughput is exactly zero with nonzero input. Warnings persist in the manifest and surface via CLI.
- **US4 (BUG-2)** — ship minimal `config/extractors/core.yaml` + `config/link_rules/core.yaml` stubs; add a rule-pack validator invoked at config load time that fails with a structured error on missing or malformed paths.
- **US5 (BUG-4)** — `node_view` dispatches on ID prefix: `doc_*` → `documents/`, `chk_*` → `chunks/`, everything else → `entities/`, with fall-through + a single not-found error.
- **US6 (BUG-3)** — add `wall_clock_started_at` / `wall_clock_finished_at` fields to the stage + ingest manifest; keep `started_at`/`finished_at` deterministic (they feed `outputs_hash`).

No new external dependencies beyond promoting the already-installed `markdown-it-py` to an explicit declaration. Constitution gates pass without justification.

## Technical Context

**Language/Version**: Python 3.10+ (existing baseline; unchanged)
**Primary Dependencies**: existing — `pyyaml`, `pypdf`, `python-docx`, `spacy` (optional), `dulwich`, `neo4j` (optional), `jsonschema` (Spec 027). **New explicit declaration**: `markdown-it-py[linkify]>=4,<5` — pure Python, already present transitively via `rich`. The `[linkify]` extra pulls in `linkify-it-py>=2,<3`, which is required at runtime for bare-URL detection per FR-016h (empirically verified: `.enable("linkify")` is a silent no-op without it). No compiled extensions added.
**Storage**: Sharded JSON under `.pkg/profiles/<profile>/` (unchanged). New entity types `ag:section`, `ag:technology`, `ag:reference` land in existing `entities/<shard>/<id>.json` layout. New link types land in existing `links/<shard>/<id>.json`. One new field on the ingest record (`source_origin`); one new field on stage manifests (`warnings`, `wall_clock_started_at`, `wall_clock_finished_at`). No new shard types, no new index files, no new schema version.
**Testing**: pytest with `--strict-markers` (existing). New files `tests/test_spec028_*.py`. Fixtures under `tests/fixtures/spec028/` using the sharded layout convention established by Specs 023/027.
**Target Platform**: Linux, macOS, WSL developer workstations (existing support matrix; unchanged).
**Project Type**: Single (existing layout under `auditgraph/`).
**Performance Goals**: Sub-entity extraction on a 1 000-file / 50 MB markdown corpus MUST complete inside the same order-of-magnitude wall time as the existing `run_extract` stage does today (reported ~387 chunks). Determinism is preserved: two runs against the same input produce byte-identical extract + index output hashes.
**Constraints**: Deterministic outputs; local-first (no network); additive-minor (backward-compatible ingest manifest reader for pre-028 shapes); no new on-disk schema version.
**Scale/Scope**: Workspaces up to ~10 000 markdown files. Orpheus report's observed workspace: 17 files / 387 chunks. Realistic upper bound for personal knowledge graphs: low thousands.

## Constitution Check

Constitution: `/home/socratesone/socratesone/auditgraph/.specify/memory/constitution.md` (v1.0.0, DrySolidTdd).

### I. DRY (Don't Repeat Yourself) — **PASS**

- New markdown extractor reuses `auditgraph.storage.hashing` (`sha256_text`, `sha256_json`), `auditgraph.storage.sharding.shard_dir`, `auditgraph.storage.artifacts.write_json`, `auditgraph.storage.ontology.resolve_type`, `auditgraph.extract.manifest.write_entities/write_claims`, `auditgraph.link.write_links`. No duplicated hashing, storage, or ID-generation code.
- Rule-pack validator is a single new function called from both `extraction.rule_packs` and `linking.rule_packs` loaders — no paste duplication across extract and link paths.
- Throughput-warning emitter is one helper called from `run_extract` and `run_index` — same shape, one code path.
- `node_view` ID-prefix dispatch is a single table-driven resolver, not repeated per-type lookup branches.

### II. SOLID Architecture — **PASS**

- **Single Responsibility**: `extract/markdown.py` has one job (markdown → sub-entities). `config/validate_rule_packs.py` (or equivalent function) has one job (reject missing paths). `pipeline/warnings.py` has one job (structured throughput advisory records).
- **Open/Closed**: New producers are added via new modules; `run_extract` gains one call site, no branch on every new producer. Legacy pre-028 ingest manifests are read through a compatibility translator — the record reader is extended, not modified per schema shape.
- **Liskov Substitution**: New entities conform to the existing entity record shape (`id`, `type`, `name`, `canonical_key`, `aliases`, `provenance`, `refs`). They are indistinguishable to downstream readers (BM25, type index, adjacency builder) from any other entity.
- **Interface Segregation**: Each new module exposes a narrow signature. The markdown extractor's authoritative signature is defined in `contracts/markdown-subentities.md` — `extract_markdown_subentities(*, source_path, source_hash, document_id, document_anchor_id, markdown_text, redactor, documents_index, pipeline_version) -> (entities, links)`. The runner reads `document_id` and `markdown_text` from the already-materialized `documents/<doc_id>.json` record; it passes the just-built note entity's id as `document_anchor_id` so the extractor can attach top-level and pre-heading origin edges. No omnibus "extractor" god-object.
- **Dependency Inversion**: Markdown parsing is accessed through a thin adapter (one function that wraps `markdown-it-py`'s `MarkdownIt().parse(text)` → a typed token iterator). The runner depends on our adapter, not on the library directly, keeping spec-028 testable without `markdown_it` patched in every test.

### III. Test-Driven Development (NON-NEGOTIABLE) — **PASS (planned)**

Every new module ships with failing tests first, per `/specs/028-markdown-extraction/tasks.md` (to be generated by `/speckit.tasks`). Concretely:

- `test_spec028_ingest_cache_origin.py` — cached files appear to extract with `parse_status == "ok"` and re-produce entities.
- `test_spec028_markdown_sections.py` — nested heading hierarchy emits parent/child links; deterministic IDs across two runs.
- `test_spec028_markdown_technologies.py` — case-fold + whitespace-trim dedup; `PostgreSQL` == `postgresql`; `PostgreSQL 16` remains distinct.
- `test_spec028_markdown_references.py` — internal/external/unresolved classification against a `documents/` store.
- `test_spec028_throughput_warnings.py` — zero-output-with-nonzero-input emits warning; nonzero-output does not.
- `test_spec028_rule_pack_validator.py` — missing path → structured error; malformed YAML → distinct error; happy path → silent success.
- `test_spec028_node_lookup.py` — `doc_*`, `chk_*`, `ent_*`, `commit_*`, `note_*` IDs each resolve; unknown ID returns structured not-found.
- `test_spec028_wall_clock_timestamps.py` — wall-clock fields reflect real time; deterministic fields stay stable across runs.
- `test_spec028_redaction_in_subentities.py` — secrets in headings, code, and link targets never reach disk.
- `test_spec028_backward_compat_reader.py` — legacy ingest manifests with `parse_status="skipped" + skip_reason="unchanged_source_hash"` are read as ok/cached.

All pre-existing tests (161 from Spec 023, full Spec 027 suite, determinism regression suite) MUST remain green. The two pre-existing known failures (spaCy unavailable, Spec 011 redaction) are unchanged.

### IV. Refactoring as a First-Class Activity — **PASS**

After each US lands green:

- Audit `parse_status` call sites across the codebase (grep showed eight, mostly in `pipeline/runner.py`, `ingest/manifest.py`) to confirm no site now needs adjustment to respect the separated `source_origin` — catch the same class of bug at its source rather than per-site.
- Extract-stage warning emitter and index-stage warning emitter share one helper; re-read after second use to confirm no accidental duplication.
- Rule-pack validator and its loader live together; verify no alternative validation path sneaked in.
- After `node_view` rewrites to prefix dispatch, confirm no other resolver re-implements the same mapping (e.g., in MCP handlers).

### V. Simplicity and Determinism — **PASS**

- No new config keys required for sub-entity extraction (spec has implicit "on by default"). A single opt-out flag honors FR-013 without adding a knob farm.
- Technology normalization is the minimum rule that satisfies Q2 (case-fold + trim); no NFKC, no punctuation stripping.
- Rule-pack stubs ship as empty but schema-versioned YAML — the minimum that satisfies FR-021 while keeping room to grow.
- All new IDs derive from source_hash + position/content; no runtime state, no clocks, no Python object identity.
- Wall-clock fields are purely informational — they never feed `outputs_hash`, preserving determinism end-to-end.

### Gate outcome

All five principles pass with no exceptions. No entries needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/028-markdown-extraction/
├── spec.md                # feature spec (already written + clarified)
├── plan.md                # this file (Phase 0–1 output)
├── research.md            # Phase 0 output: decisions + rationale
├── data-model.md          # Phase 1 output: entity + record shapes
├── quickstart.md          # Phase 1 output: how to verify the feature end-to-end
├── contracts/             # Phase 1 output: interface schemas
│   ├── markdown-subentities.md     # extract_markdown_subentities(...) contract
│   ├── ingest-record-v2.md         # updated ingest record with source_origin
│   ├── stage-manifest-warnings.md  # warnings[] schema on StageManifest
│   ├── node-view-dispatch.md       # node_view ID-prefix resolver contract
│   └── rule-pack-validator.md      # rule-pack loader preconditions + errors
├── checklists/
│   └── requirements.md    # spec quality checklist (already written)
└── tasks.md               # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
auditgraph/
├── cli.py                               # (TOUCH) node dispatch + surface warnings in _emit()
├── config.py                            # (TOUCH) call rule-pack validator at load; add helper
├── ingest/
│   ├── manifest.py                      # (TOUCH) record shape adds source_origin, wall_clock_*
│   ├── parsers.py                       # (TOUCH) _build_document_metadata persists redacted
│   │                                    #         `text` on markdown document payloads (FR-015a)
│   └── sources.py                       # (TOUCH) build_source_record accepts source_origin
├── extract/
│   ├── entities.py                      # (no change — build_note_entity unchanged)
│   └── markdown.py                      # (NEW) sub-entity extractor
├── pipeline/
│   ├── runner.py                        # (TOUCH) run_ingest sets source_origin; run_extract
│   │                                    #         reads parse_status only; call markdown
│   │                                    #         extractor; emit warnings; use wall_clock_*
│   └── warnings.py                      # (NEW) ThroughputWarning + emit helpers
├── query/
│   └── node_view.py                     # (TOUCH) ID-prefix dispatch
├── storage/
│   ├── hashing.py                       # (TOUCH) add wall_clock_now() helper (not a new hash)
│   └── manifests.py                     # (TOUCH) StageManifest/IngestManifest add fields
└── utils/
    └── rule_packs.py                    # (NEW) RulePackValidator + structured errors

config/
├── pkg.yaml                             # (unchanged — still references the stubs below)
├── extractors/
│   └── core.yaml                        # (NEW) empty but schema-versioned stub
└── link_rules/
    └── core.yaml                        # (NEW) empty but schema-versioned stub

tests/
├── fixtures/
│   └── spec028/
│       ├── single_section.md
│       ├── nested_headings.md
│       ├── code_and_links.md
│       ├── with_secrets.md
│       └── workspace/                   # a multi-file corpus for end-to-end tests
├── test_spec028_ingest_cache_origin.py         # US1
├── test_spec028_backward_compat_reader.py      # US1 (legacy manifest shape)
├── test_spec028_markdown_sections.py           # US2
├── test_spec028_markdown_technologies.py       # US2
├── test_spec028_markdown_references.py         # US2
├── test_spec028_markdown_determinism.py        # US2 (byte-identical reruns)
├── test_spec028_redaction_in_subentities.py    # US2 × Spec-027
├── test_spec028_throughput_warnings.py         # US3
├── test_spec028_rule_pack_validator.py         # US4
├── test_spec028_node_lookup.py                 # US5
└── test_spec028_wall_clock_timestamps.py       # US6

llm-tooling/
└── tool.manifest.json                   # (TOUCH) register new ag:* types as filterable in
                                         #         existing ag_list / ag_query tool schemas;
                                         #         run skill.md + adapters generators after
```

**Structure Decision**: Single-project layout (existing). No monorepo restructure, no new top-level directory. Every new module sits beside an existing peer (`extract/markdown.py` ↔ `extract/adr.py` / `extract/logs.py` / `extract/ner.py`; `pipeline/warnings.py` ↔ `pipeline/runner.py` / `pipeline/postcondition.py`; `utils/rule_packs.py` ↔ `utils/redaction.py` / `utils/budget.py`). New tests follow the `test_spec<NNN>_*.py` naming convention established by Specs 023 / 025 / 027.

## Complexity Tracking

*Not applicable — the Constitution Check passed all five principles without justification. No 4th project, no repository pattern, no cross-cutting abstraction above what the existing extract/pipeline/storage modules provide.*
