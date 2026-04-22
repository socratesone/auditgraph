# Feature Specification: Markdown ingestion produces honest, queryable results

**Feature Branch**: `028-markdown-extraction`
**Created**: 2026-04-20
**Status**: Draft
**Input**: User description: "Review reports/Orpheus.md — external consumer diagnostic report on auditgraph v0.1.0. On a plain-markdown corpus the pipeline reports success at every stage yet yields 0 queryable entities. The report catalogs 5 bugs and proposes markdown sub-entity extraction as the underlying capability gap. Create spec-028 from this report."

## Clarifications

### Session 2026-04-20

- Q: Naming convention for the new markdown entity types? → A: `ag:section`, `ag:technology`, `ag:reference` — colon-namespaced, matches the wording in `CLAUDE.md` and the prefix style established by `ner:person`.
- Q: Technology-token normalization rule for per-document dedup? → A: Case-fold plus strip leading/trailing whitespace; no other transformations. `PostgreSQL` and `postgresql` collapse to one entity per document; `PostgreSQL 16` remains distinct from `PostgreSQL`.
- Q: What counts as "in-corpus" for `ag:reference` classification? → A: A reference is classified as internal only when its target resolves to a document already materialized in the profile store (under `documents/<doc_id>.json`) in the same run. Targets that look in-workspace but were not ingested are "unresolved"; URL-shaped targets that are not internal are "external".
- Q: Migration behavior for existing workspaces when spec-028 ships? → A: Automatic. The next pipeline run detects that the extract-stage producer set has changed and re-extracts against the full corpus so new-type entities appear without any manual rebuild. Cached outputs from pre-028 runs are treated as stale for the extract stage only; ingest-stage caches remain valid to keep the upgrade run fast.
- Q: Threshold semantics for throughput warnings? → A: Fire only when a stage produces exactly zero output given ≥1 input from the prior stage. Ratio-based or comparative thresholds are out of scope for this spec; they can be added later without breaking the binary contract.

### Session 2026-04-20 (post-review adjustments)

Recorded decisions from the review in `specs/028-markdown-extraction/adjustments.md`. Each decision is applied in the FRs, data model, contracts, tasks, and quickstart in the same pass.

- A1: Entity ID inputs for `ag:section`, `ag:technology`, `ag:reference` ALL include `source_hash` as their first component. The `canonical_key` entity field is distinct: it is the human-readable key (slug path / normalized token / raw target) used for display and graph-merge affinity; the ID is `ent_<sha256_text(source_hash + "::" + type + "::" + canonical_key + "::" + order_if_needed)>`.
- A2: Redacted full markdown text is persisted on the `document` record (new `text` field in `documents/<doc_id>.json`). The extract stage reads this field. No re-reading of source files from disk, no second redaction pass. `extract_markdown_subentities` stays pure.
- A3: Reference resolution uses a bi-directional index with both `doc_id → path` and normalized `source_path → doc_id` maps. Relative link resolution: normalize against source file's parent then workspace-relative. Fragment-only (`#anchor`) → unresolved. Combined `path#fragment` → classify on path portion. Query strings → strip, classify on path. Directory / bare-name targets → unresolved (no README.md auto-resolution in v1). URL-encoded paths → URL-decoded before resolution.
- A4: Reference link topology unified — one edge from the enclosing section to the `ag:reference` entity (type `references`), and one edge from the `ag:reference` to the resolved document (type `resolves_to_document`) only when resolution is internal. External and unresolved references emit no second edge — their classification is a field on the reference entity, not a graph topology.
- A5: Pruning — when a markdown source is re-extracted, the pipeline MUST remove all prior `ag:section` / `ag:technology` / `ag:reference` entities AND their originating markdown links whose primary source reference points at that source path, before writing the refreshed sub-entities. Pruning is type-scoped — `note`, NER, git-provenance, and any user-introduced entities are NEVER pruned by this mechanism.
- A6: Source-level cooccurrence linking (`link.source_cooccurrence.v1`) MUST exclude `ag:section`, `ag:technology`, and `ag:reference` entities. The explicit markdown links are the canonical graph edges for these types.
- A7: Quickstart — expected counts, determinism check, and empty-pipeline demo are corrected to match real extractor output. Empty-pipeline demo uses a `.txt` source (note entity does not fire) rather than a markdown stub.
- A8: Init copies the shipped stub rule-packs (`extractors/core.yaml` and `link_rules/core.yaml`) alongside `pkg.yaml`. Shipped wheels include the stubs as package data. Validator falls back to package resources if workspace-local stubs are absent.
- A9: Fenced code blocks emit exactly one `ag:technology` entity whose token is the block's `info` string (language tag) — NOT per-line or per-word. Empty info string ⇒ no entity. Inline code spans emit one entity per span. Images are ignored in v1 (out of scope). Bare URLs are captured when `markdown-it-py` `linkify` option is enabled — the spec enables it.
- A10: Warnings appear in exactly one nested location: `StageResult.detail["warnings"]` in the live result and under the top-level `warnings` key in the persisted stage manifest. `_emit` is the pass-through; it does not transform the shape.
- A11: `markdown-it-py` pinned to `>=4,<5` to match the `uv.lock` (4.0.0). The token-stream API we rely on (`MarkdownIt.parse(text)`) is backward compatible with 3.x.
- A12: A reviewer acceptance checklist is added under `checklists/` to guard against the categories of drift this review surfaced (contradictions across artifacts, quickstart fidelity, stale-entity coverage).

## User Scenarios & Testing *(mandatory)*

<!--
  Scenarios below are ordered by user-observable impact: the highest-priority stories
  fix the false-success failure mode and add the structural capability that makes
  markdown actually queryable; the middle-priority stories surface honest status and
  honest defaults; the low-priority stories polish navigation and audit trust. Each
  story is independently testable — implementing any one delivers standalone value.
-->

### User Story 1 - Repeated runs on a markdown corpus keep producing entities (Priority: P1)

An engineer initializes auditgraph in a documentation repository containing only markdown files, runs the pipeline, and then runs it again after making a small edit. Today the second run silently drops all entities because the ingest stage marks cached files as "skipped" and the extract stage filters those out — so the user ends up with a workspace that reports success but contains zero entities.

**Why this priority**: This is the highest-impact defect in the system. It turns a working pipeline into a broken one the moment the user reruns it — which is the normal case for incremental ingestion. Until this is fixed, no other improvement in the spec can be observed reliably, because any rerun of a test fixture will empty the entity store.

**Independent Test**: In a fresh workspace with a single markdown file, run the full pipeline, record entity count N (N > 0). Edit an unrelated file, run the pipeline again. Entity count must still be N. Run a third time with no edits. Entity count must still be N.

**Acceptance Scenarios**:

1. **Given** a markdown-only corpus and a successful first run that produced N entities, **When** the user runs the pipeline a second time without editing any file, **Then** the entity count remains N and queries return the same results.
2. **Given** a markdown-only corpus with entities already materialized, **When** the user edits one file and reruns, **Then** entities from unchanged files remain present and entities from the edited file are refreshed.
3. **Given** a file that genuinely failed to parse on a prior run, **When** the user reruns the pipeline, **Then** the failed file is retried (not treated as reusable cached output) and its failure status is surfaced.

---

### User Story 2 - Markdown documents expose queryable sub-structure (Priority: P1)

An engineer has a documentation workspace with hundreds of markdown files. They want to ask questions like "which sections mention PostgreSQL?", "which documents link to our ADR on retries?", "what technologies are referenced across the corpus?". Today auditgraph produces at most one coarse `note` entity per markdown file, so these queries are impossible without enabling NER (which is off by default and produces poor results on technical content).

**Why this priority**: This is the capability gap the report names as spec-028's purpose. One note entity per file cannot support the queries users actually run against documentation. Adding deterministic, rule-based structural entities makes the most common ingestion target — developer markdown — useful out of the box. Paired with US1 at P1 because either alone delivers independent value: US1 without US2 still produces honest note-level entities across reruns; US2 without US1 still produces rich sub-entities on every first run.

**Independent Test**: Ingest a fixture containing a markdown file with three nested headings, two inline code tokens, one fenced code block, and three link styles (inline, reference, bare URL). After the pipeline runs, the entity store contains at least one entity per heading, one entity per distinct code token, and one entity per link target. Run the pipeline again: entity IDs are byte-identical.

**Acceptance Scenarios**:

1. **Given** a markdown file with nested headings (H1 → H2 → H3), **When** the pipeline runs, **Then** each heading produces a distinct section entity and the entities carry a parent-child relationship reflecting the heading hierarchy.
2. **Given** a markdown file containing inline code spans and fenced code blocks, **When** the pipeline runs, **Then** each distinct code token is emitted as a technology entity, deduplicated within the document.
3. **Given** a markdown file containing inline links, reference-style links, and bare URLs, **When** the pipeline runs, **Then** each link produces a reference entity whose target is recorded (and classified as internal vs external where determinable).
4. **Given** the same markdown input, **When** the pipeline runs twice, **Then** the resulting entity IDs, link IDs, and pipeline manifest hashes are byte-identical across runs.
5. **Given** a section body containing credential-shaped strings, **When** the pipeline runs, **Then** the emitted section entity's body is redacted before it is written to disk.
6. **Given** a markdown file, **When** the user runs the existing list/query commands filtered by the new entity types, **Then** the new types appear as first-class filter values and return the expected entities.

---

### User Story 3 - The pipeline loudly reports when it produced nothing (Priority: P2)

An engineer misconfigures their workspace — maybe they set include paths that match no files, maybe they disabled all entity producers, maybe they are hitting a regression. Today every stage reports `status: ok` even when the end result is zero entities and an empty index. The engineer has no signal, short of reading source code, that something went wrong.

**Why this priority**: An honest empty-result signal converts silent failure into a diagnosable error. It doesn't by itself fix any specific bug — but it prevents the next class of "looked successful, wasn't" problems from reaching users. Priority is P2 because the tool is still usable without it (if US1 and US2 ship, the empty-pipeline case becomes rare), but as the report demonstrates, the combination of false-success and zero-output is the worst possible user experience.

**Independent Test**: Configure a workspace so that ingestion succeeds but no entity producer is active (e.g., empty content, all producers disabled). Run the pipeline. The CLI output and the persisted manifest must surface a structured warning identifying which stage had unexpectedly low or zero throughput. Exit code remains unchanged (warnings, not errors).

**Acceptance Scenarios**:

1. **Given** a run where ingest succeeded for ≥1 source but extract produced 0 entities, **When** the pipeline completes, **Then** the run reports a structured warning indicating zero entities produced and includes a hint about likely causes.
2. **Given** a run where extract produced ≥1 entity but the index is empty, **When** the pipeline completes, **Then** the run reports a distinct structured warning identifying the empty-index condition.
3. **Given** a run where every stage produced meaningful output, **When** the pipeline completes, **Then** no throughput warnings are emitted.
4. **Given** warnings are emitted by any stage, **When** the user inspects the persisted run manifest, **Then** the warnings are retrievable later from the same manifest (not only from live CLI output).

---

### User Story 4 - Shipped default configuration never references paths that don't exist (Priority: P2)

An engineer runs `auditgraph init` to generate a starter config, then runs the pipeline. Today the shipped default config references rule-pack files that don't exist in the installed package — so the extraction and linking stages silently run with zero rules, and the user has no indication that their config is broken out of the box.

**Why this priority**: This is a setup-time trust problem. A tool whose default config doesn't match its shipped files cannot be trusted by new users. Priority is P2 rather than P1 because it doesn't directly cause the zero-entity failure mode today (the missing files are currently benign — no rule packs are expected by downstream stages), but it is user-hostile: the user has no way to know their baseline install is pointing at ghost files.

**Independent Test**: Install auditgraph in a fresh environment, run `auditgraph init` to produce the default config, then start the pipeline. Either every path the config references exists in the installation, or the pipeline emits a clear, actionable error pointing at the missing path. The pipeline must not silently proceed with declared-but-unreadable rule packs.

**Acceptance Scenarios**:

1. **Given** a fresh install of auditgraph, **When** the user runs `auditgraph init` and then `auditgraph run`, **Then** either (a) every path referenced in the generated default config exists, or (b) the pipeline fails with an error naming the missing file.
2. **Given** the user edits their config to reference a nonexistent rule-pack path, **When** they run the pipeline, **Then** the pipeline surfaces a structured error identifying the missing file before any stage silently runs without those rules.
3. **Given** the user edits their config to reference a rule pack that exists but is malformed, **When** they run the pipeline, **Then** the pipeline surfaces a structured error distinct from the "missing file" error above.

---

### User Story 5 - Users can navigate to any entity class by ID (Priority: P3)

An engineer inspects a run and wants to view a document node by its ID (`doc_…`). Today the `auditgraph node` command assumes every ID lives under the `entities/` tree — so documents, which live under `documents/`, return `No such file or directory` errors. The user has to know the on-disk layout to work around it.

**Why this priority**: Navigation is a first-class affordance — when it fails on a first-class artifact, users lose trust in the CLI. But the command works for the majority of IDs, and workarounds exist. Priority is P3: important for polish but not blocking the main markdown-ingestion journey.

**Independent Test**: Run the pipeline on any workspace. Take a known document ID, a known chunk ID, and a known entity ID from the output. Invoke the navigation command with each ID. All three must resolve to the correct on-disk record regardless of which subtree the record lives under.

**Acceptance Scenarios**:

1. **Given** a materialized document, **When** the user invokes the node lookup with its `doc_…` ID, **Then** the document record is returned.
2. **Given** a materialized chunk, **When** the user invokes the node lookup with its `chk_…` ID, **Then** the chunk record is returned.
3. **Given** a materialized entity, **When** the user invokes the node lookup with its `ent_…` ID, **Then** the entity record is returned.
4. **Given** an ID that does not exist in any subtree, **When** the user invokes the node lookup, **Then** a single structured not-found error is returned (not a path-specific error from one subtree).

---

### User Story 6 - Run manifests carry truthful timestamps (Priority: P3)

An operator audits a production run and reads its manifest, expecting to see when each stage started and finished. Today every manifest carries a fixed placeholder timestamp (`1995-12-23T04:33:39Z`) because a determinism-test fixture is bleeding into the production code path.

**Why this priority**: The placeholder undermines audit trust. Anyone reading a manifest can tell the timestamps are fake. However, nothing functional breaks: deterministic hashes are preserved because they don't depend on wall-clock time. Priority is P3 — cosmetic but credibility-damaging.

**Independent Test**: Run the pipeline, wait a known interval, run it again. Inspect the manifests from both runs. Wall-clock timestamp fields must differ between runs and must fall within a sensible window of each actual invocation. Deterministic fields used for output hashing remain stable.

**Acceptance Scenarios**:

1. **Given** the user runs the pipeline, **When** they inspect the manifest afterward, **Then** the wall-clock started-at and finished-at fields reflect the actual invocation time.
2. **Given** two runs against identical input, **When** the user inspects the manifests, **Then** fields that feed the output hash are identical between runs while wall-clock fields differ.
3. **Given** the test suite runs the pipeline with a pinned clock, **When** the tests assert hash stability, **Then** they continue to pass; deterministic identifiers remain deterministic.

---

### Edge Cases

- What happens when a markdown file contains only frontmatter and no body? The document still produces a note entity; no section/technology/reference entities are required.
- What happens when a markdown file contains a heading but empty body? The section entity is emitted with an empty body snippet; parent-child links still form against surrounding headings.
- What happens when the same code token appears many times in one document? It is deduplicated to a single technology entity per document, preserving the first occurrence for provenance.
- What happens when a link target is a broken or unresolvable relative path? The reference entity is still emitted; it is classified as "unresolved" rather than dropped, so the user can see the dangling reference.
- What happens when a file's cached hash matches on disk but the cached output is missing or corrupted? The file is re-parsed rather than treated as a valid cache hit.
- What happens when a workspace genuinely has zero natural inputs (e.g., all excluded by include_paths)? Per FR-017 the binary threshold requires ≥1 upstream input before a warning fires, so a fully-empty corpus produces no warning. The empty-throughput warning specifically distinguishes "ingested ≥1 file but produced 0 entities" from "nothing to ingest in the first place."
- What happens when a user explicitly disables markdown sub-entity extraction? Existing note-level behavior is preserved; no new entity classes are emitted.
- What happens when running on a non-markdown parser (PDF, DOCX, log, ADR)? Sub-entity extraction does not activate; existing behavior for those parsers is unchanged.
- What happens when a credential-shaped string appears in a section heading itself (not the body)? The heading text is redacted before the section entity is written, consistent with existing parser-entry redaction.
- What happens when a user edits a heading's text, causing its section's ID (rooted in `source_hash`) to change on the next run? The pruning mechanism (FR-016c) removes the old-hash section entity; the new-hash entity takes its place. No stale orphan accumulates.
- What happens when a reference target is a fragment-only anchor (`[link](#install)`)? The reference entity is emitted with `resolution="unresolved"` — in-document anchor resolution is explicitly out of scope for v1.
- What happens when a reference target combines a path and a fragment (`[link](setup.md#install)`)? Classification runs on the path portion only (`setup.md`); the fragment is preserved in the entity's `target` field for display but does not affect resolution.
- What happens when a markdown source contains a fenced code block with no language info string? No `ag:technology` entity is emitted for that block (FR-016g). Inline code within the block's body is also not mined for tokens.
- What happens when a markdown source contains an image (`![alt](diagram.png)`)? No reference or technology entity is emitted in v1. Images are out of scope.
- What happens when a markdown source contains a code span or link BEFORE the first heading? The `ag:technology` or `ag:reference` entity is still emitted; its originating edge (`mentions_technology` / `references`) attaches to the `note` (document anchor) entity rather than to a section. See `contracts/markdown-subentities.md` "Pre-heading content" for the authoritative rule.
- What happens when a markdown source has NO headings at all (just a paragraph of prose with some inline code and a link)? Exactly the same rule applies: every emitted sub-entity's originating edge attaches to the note entity. Zero `ag:section` entities exist for this source, but `ag:technology` and `ag:reference` entities can still exist and be queryable.

## Requirements *(mandatory)*

### Functional Requirements

#### Cache handling and extract participation (US1)

- **FR-001**: The pipeline MUST treat successfully-ingested files whose source hash matches a prior run as participating inputs to downstream stages, not as skipped inputs.
- **FR-002**: The pipeline MUST distinguish between "this file parsed successfully" and "this file's parse output was reused from cache" in its persisted manifest, so that downstream filters operate on correctness (did it parse?) rather than on execution origin (was it cached?).
- **FR-003**: Downstream stages (extract, index) MUST consume all successfully-parsed files from each run, whether their content was freshly parsed or reused from cache.
- **FR-004**: A file that genuinely failed to parse MUST continue to be excluded from downstream stages and MUST be retried on the next run.
- **FR-005**: When cached output is expected but missing or corrupted, the pipeline MUST re-parse the file from source rather than treat the missing cache as success.

#### Markdown sub-entity extraction (US2)

- **FR-006**: The pipeline MUST extract section entities of type `ag:section` from markdown documents, one per heading, preserving the heading's text and its position in the document hierarchy.
- **FR-007**: The pipeline MUST record parent-child relationships between `ag:section` entities so that a nested heading structure (H1 → H2 → H3) is traversable as a link topology.
- **FR-008**: The pipeline MUST extract technology entities of type `ag:technology` from **inline code spans and fenced code block language info strings** (NOT fenced code block body content — see FR-016g for the detailed token-emission rule), deduplicated within each document by normalized token. Normalization MUST be case-folding plus stripping of leading and trailing whitespace, with no other transformations — `PostgreSQL` and `postgresql` collapse to one entity per document, while `PostgreSQL 16` remains distinct from `PostgreSQL`.
- **FR-009**: The pipeline MUST extract reference entities of type `ag:reference` from inline links, reference-style links, and bare URLs, recording the link target for each.
- **FR-010**: `ag:reference` entities MUST be classified into exactly one of three resolution states — users MUST be able to distinguish them:
  - **internal**: the target resolves to a document already materialized in this profile's `documents/` store during the same run.
  - **external**: the target is URL-shaped (has an explicit scheme such as `http://` or `https://`) and is not classified as internal.
  - **unresolved**: every other case, including relative paths whose target was not ingested, targets that look in-workspace but have no corresponding document record, and links with malformed targets.
- **FR-011**: Sub-entity extraction MUST be fully deterministic: two runs against identical markdown input MUST produce byte-identical entity IDs, link IDs, and the extract stage's output hash.
- **FR-012**: Sub-entity extraction MUST activate by default for every markdown source; no configuration change MUST be required to observe it on a fresh install.
- **FR-013**: Sub-entity extraction MUST be controllable — users MUST be able to opt out via configuration without disabling other extraction paths.
- **FR-014**: Existing entity types, link types, and other extraction paths MUST NOT change behavior as a consequence of adding markdown sub-entities.
- **FR-015**: Sub-entity text written to disk MUST pass through the existing parser-entry redaction so that credential-shaped strings in section bodies, inline code, or link targets are redacted before storage.
- **FR-015a**: The ingest stage MUST persist the redacted full markdown text on the `document` record (`documents/<doc_id>.json`) for every source with `parser_id == "text/markdown"`. The extract stage MUST read this field to feed the markdown sub-entity extractor; it MUST NOT re-read the source file from disk and MUST NOT re-run redaction. The parser-entry redaction (Spec 027 FR-016) remains the canonical and only redaction site.
- **FR-016**: Users MUST be able to filter, list, and navigate the new entity types using existing query and list commands — the new types MUST be first-class facets in any type-filtered view.
- **FR-016a**: On an existing workspace whose last pipeline run predates spec-028, the next pipeline run MUST automatically re-run the extract stage against the full corpus so that `ag:section` / `ag:technology` / `ag:reference` entities appear without the user issuing any explicit rebuild or configuration change.
- **FR-016b**: Automatic re-extraction MUST NOT require invalidating any ingest-stage cache broadly: source-hash-keyed cached ingest records MUST remain valid and reach the extract stage (per FR-001 and FR-003) so the upgrade run does not re-parse unchanged sources. No extract-stage cache-invalidation mechanism is required, because the extract stage re-processes every successfully-parsed record on each invocation.
- **FR-016b1**: The ingest stage's cache-hit branch (matching `source_hash`) MUST validate that the cached `documents/<doc_id>.json` payload carries every field that the current spec requires for its parser. For `parser_id == "text/markdown"`, this means the `text` field (per FR-015a) MUST be present. When a cache hit is found but the required field is missing, the ingest stage MUST treat the cache as incomplete for THIS source only — reparse and redact the source once, write the refreshed document record (now with `text`), and record the result as `parse_status="ok"`, `source_origin="fresh"` (not `cached`). All other cache hits remain valid. This is the upgrade path for pre-028 workspaces: after one run, every markdown document record carries `text` and subsequent runs read from cache normally.
- **FR-016b2**: Cache-completeness checks MUST be scoped to the fields the ingest stage itself is responsible for. The extract stage MUST NOT perform file-level cache invalidation — it reads cached document records as-is. If a required field is missing from an extract-stage input, the correct failure mode is an explicit error (not silent empty output). The cache-refresh decision belongs exclusively to the ingest/cache layer.
- **FR-016c**: When a markdown source is (re-)extracted, the pipeline MUST remove every on-disk `ag:section`, `ag:technology`, and `ag:reference` entity whose `refs[0].source_path` matches the current source path, AND every link whose `rule_id` names a markdown sub-entity producer rule AND whose `from_id` or `to_id` matches one of the pruned entity IDs — BEFORE writing the refreshed sub-entities for that source. The algorithmic specification is in `data-model.md §5`. Pruning prevents stale entities from accumulating when a user edits a markdown file (source-hash-rooted IDs rotate on edit) and does not depend on link records carrying a `source_path` field.
- **FR-016d**: The pruning mechanism specified in FR-016c MUST be scoped strictly to the three markdown sub-entity types and their originating link rule IDs. Entities of other types (`note`, any `ner:*`, git-provenance commit/tag/author/file/repo records, user-introduced types) MUST NOT be pruned by this mechanism.
- **FR-016e**: Source-level generic cooccurrence linking (the existing `link.source_cooccurrence.v1` rule in `auditgraph/link/rules.py`) MUST exclude `ag:section`, `ag:technology`, and `ag:reference` entities. Cooccurrence edges between markdown sub-entities would be O(n²) noise; the explicit markdown link types (`contains_section`, `mentions_technology`, `references`, `resolves_to_document`) are the canonical graph edges for these types.
- **FR-016f**: The reference-resolution index passed to the markdown sub-entity extractor MUST support both directions — mapping document IDs to source paths AND mapping normalized workspace-relative source paths to document IDs — so that a markdown target like `./setup.md` from source `docs/intro.md` resolves to the corresponding `doc_…` ID without scanning all documents. Fragment-only targets (`#anchor`) classify as `unresolved`; combined targets (`setup.md#install`) classify on the path portion only; query strings are stripped before resolution; directory or bare-name targets (no extension) classify as `unresolved` (no README.md auto-resolution in v1); URL-encoded paths are URL-decoded before resolution.
- **FR-016g**: `ag:technology` token emission rules are: (a) each inline code span (`` `token` ``) emits one `ag:technology` entity with the span content as the token; (b) each fenced code block emits exactly one `ag:technology` entity whose token is the block's `info` string (language tag such as `bash`, `python`); a fenced block with an empty info string emits no entity; (c) indented code blocks emit no `ag:technology` entity (no info string is available); (d) images (`![alt](src)`) do NOT produce `ag:reference` entities in v1.
- **FR-016h**: Bare URL detection MUST be enabled in the markdown parser (`markdown-it-py` `linkify` option) so that autolinks (`<https://example.com>`) AND plain-text URLs (`https://example.com`) both materialize as `ag:reference` entities. Reference-style links (`[text][label]` + `[label]: url`) MUST resolve via the parser's built-in link resolution and emit `ag:reference` like any other link.
- **FR-016i**: When `extraction.markdown.enabled == false` (the opt-out flag introduced by FR-013), the pipeline MUST make BOTH the markdown sub-entity producer AND the pruning helper (FR-016c) inert for the entire run. Consequence: previously-emitted markdown sub-entities remain on disk unchanged — disabling the feature does NOT retroactively clean up the entity store. Users who want a clean slate MUST either (a) delete `.pkg/profiles/<profile>/entities/<shard>/` entries matching the markdown sub-entity types, or (b) rebuild from scratch with the flag enabled and then disable. This is the deliberate v1 behavior — the pruner stays inert when disabled so the flag is a pure activation switch, not a cleanup command.

#### Honest pipeline status (US3)

- **FR-017**: When a stage completes successfully and produces exactly zero output records while having received ≥1 input from the prior stage, the stage MUST emit a structured warning identifying the shortfall (e.g., "ingested N files, wrote 0 entities"). Ratio-based or comparative thresholds are out of scope for this requirement; the contract is binary (zero vs nonzero output).
- **FR-018**: Throughput warnings MUST be persisted in the stage's run manifest, not only displayed in live CLI output, so that an operator inspecting the run later can see them.
- **FR-019**: Throughput warnings MUST NOT change stage exit status on their own; the pipeline MUST continue to complete successfully when stages merely produced nothing (this is not an error per se, just a noteworthy condition).
- **FR-020**: Each throughput warning MUST include an actionable hint pointing the user at the most likely causes.

#### Honest default configuration (US4)

- **FR-021**: The default configuration shipped with an install MUST NOT reference file paths that don't exist in the installed package.
- **FR-022**: When a user's configuration references a rule-pack or similar resource path that cannot be located, the pipeline MUST fail with a structured error identifying the missing path — it MUST NOT silently proceed with the resource absent.
- **FR-023**: When a referenced resource exists but fails to parse or validate, the pipeline MUST emit a structured error distinct from the "missing file" error.

#### Navigation (US5)

- **FR-024**: The node-lookup command MUST resolve an entity ID to its record regardless of which on-disk subtree the record lives in (entities, chunks, documents, or any future class).
- **FR-025**: When a node ID does not exist anywhere in the store, the lookup MUST return a single not-found error, not a path-specific error from the first subtree tried.
- **FR-026**: Existing navigation behavior for entity IDs already supported MUST be preserved — new ID-class dispatch MUST be additive.

#### Truthful manifests (US6)

- **FR-027**: Run manifests MUST carry wall-clock start and finish timestamps that reflect the actual invocation wall time.
- **FR-028**: Fields used to compute deterministic output hashes MUST remain independent of wall-clock time; deterministic reproducibility across runs MUST NOT regress.
- **FR-029**: A test-only mechanism for pinning time for determinism tests MUST remain available, but it MUST NOT default on in production code paths.

### Key Entities *(include if feature involves data)*

- **Section** (`ag:section`): A heading-anchored unit within a markdown document. Carries a title, a body snippet, a position/order within the document, and a link to its parent section (for nested headings).
- **Technology** (`ag:technology`): A distinct code-like token appearing in a markdown document. Identity is the case-folded, whitespace-trimmed token; the entity also preserves the first-occurrence verbatim text and location for provenance.
- **Reference** (`ag:reference`): A link from a markdown document to an internal document, an external URL, or an unresolved target. Records the raw target string, the classification (internal / external / unresolved), and the originating section. Graph topology: every reference receives one inbound edge of type `references` from its enclosing section; only internal references receive an additional outbound edge of type `resolves_to_document` pointing at the target `doc_…` record.
- **Throughput warning**: A structured, persistent advisory emitted by a pipeline stage when its output is unexpectedly empty or near-empty given its input. Carries the stage name, the shortfall kind, and an actionable hint.
- **Source origin**: A per-file annotation in the ingest manifest distinguishing fresh parse vs cache reuse. Orthogonal to parse status (ok/failed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fresh install, a user can run `auditgraph init` followed by the full pipeline on a markdown-only corpus and observe entities > 0 without editing any configuration.
- **SC-002**: Running the pipeline a second time on the same corpus with no source changes produces the same entity and link counts as the first run.
- **SC-003**: On a representative documentation fixture, sub-entity extraction emits at least one section entity per heading and at least one reference entity per distinct link, measured by a fixture test whose expected counts are known in advance.
- **SC-004**: Two pipeline runs against identical markdown input produce byte-identical extract-stage and index-stage output hashes.
- **SC-005**: In a run where every stage succeeds but the extract stage produced zero entities, the user can determine that fact from CLI output or from the persisted manifest alone, without reading source code.
- **SC-006**: A fresh install's default configuration passes a "no orphan references" check — every file path the config names is readable from the installation, or the pipeline fails loudly at startup.
- **SC-007**: For every materialized entity class (entity, chunk, document, and any new class added by this spec), invoking node lookup by ID returns the correct record on the first attempt.
- **SC-008**: Inspecting a manifest after a pipeline run, the wall-clock timestamp fields fall within 60 seconds of the actual invocation time (the bound is loose because stage duration on large corpora is bounded by I/O, not by the helper; the test fixture's expected bound is under 5 s).
- **SC-009**: The existing determinism test suite continues to pass, confirming that the timestamp fix did not regress output-hash reproducibility.
- **SC-010**: Queries filtered by the new entity types (`ag:section`, `ag:technology`, `ag:reference`) return results on a markdown corpus — confirming that listing, filtering, and navigation commands treat the new types as first-class facets.
- **SC-011**: Starting from a workspace populated by a pre-028 pipeline run (whose `documents/<doc_id>.json` records lack the new `text` field), a single subsequent pipeline invocation — with no manual rebuild and no configuration change — refreshes each markdown document's `text` field exactly once and produces at least one `ag:section`, one `ag:technology`, or one `ag:reference` entity from an eligible markdown source. Non-markdown cached documents MUST be unaffected: their records retain no `text` field and do not trigger a reparse.
- **SC-012**: After a user edits a heading in a markdown file and reruns the pipeline, the entity store contains no orphan section entity keyed on the pre-edit source hash. The count of `ag:section` entities for that source reflects only the current file's headings.
- **SC-013**: For a workspace of N markdown sources producing a total of E sub-entities (sections + technologies + references), the number of `link.source_cooccurrence.v1` edges emitted is strictly bounded by the count of non-markdown-sub-entity entities sharing sources — i.e., cooccurrence is not amplified by the new types. Measured by asserting that no cooccurrence link has **EITHER endpoint** in `{ag:section, ag:technology, ag:reference}` (per FR-016e — markdown sub-entities are excluded from the cooccurrence graph entirely, not just excluded from same-type pairs).

## Assumptions

- Cached parse output on disk is trustworthy once its source hash matches; if users need to invalidate cache they can do so via existing means (deleting the cache directory, changing the content).
- The existing extension routing (markdown files → markdown parser) is a sufficient signal for activating sub-entity extraction; no document classification is required at this spec's scope. If spec-024 later introduces classification, sub-entity extraction can be refined to gate on class without a breaking change to this spec.
- Parser-entry redaction (introduced in spec-027) is the canonical redaction site for all entity text emitted during the extract stage; new sub-entity producers route their text through the same site rather than adding a new redaction pass.
- Determinism is preserved by existing ID-generation patterns in the codebase; new sub-entity IDs follow the same deterministic hashing discipline (source hash plus stable positional/content inputs, no runtime state).
- Throughput warnings are advisory — they do not change exit codes and do not gate further stages from running. Users who want warnings-as-errors can layer their own check on the persisted manifest.
- The fix for orphan rule-pack paths may be satisfied by shipping minimal default rule packs, by failing loud on missing paths, or by both; the user-observable contract is "no silent misconfiguration."
- The fix for the node-lookup command may be satisfied by ID-prefix dispatch or by promoting documents to first-class entity status; the user-observable contract is "lookup resolves by ID regardless of subtree."

## Dependencies

- **No blocking dependency on spec-024 (document classification).** Sub-entity extraction in this spec uses the already-available `text/markdown` parser signal. If spec-024 later ships, sub-entity activation can be refined to gate on classification as a small additive change.
- **Spec-027 (security hardening) parser-entry redaction contract is a precondition** for sub-entity text handling (FR-015). This spec relies on Spec-027's canonical redaction site rather than introducing a new one.
- **Spec-023 (local query filters & type index) is a precondition** for surfacing the new entity types in type-filtered list and query commands (FR-016). No change to spec-023 is required; new types register into the same type index infrastructure.
- **Spec-025 (remove code extraction) scope is preserved.** This spec does not re-ingest source-code files or add code-aware chunking. Technology entities extracted from markdown code spans are lightweight tokens pulled from markdown content, not from the code files themselves.

## Out of Scope

- Model-based markdown entity extraction (LLM or embedding-based). Sub-entity extraction here is rule-based and deterministic.
- PDF and DOCX sub-entity extraction. The same pattern could later apply to other parsers, but this spec covers only markdown.
- Semantic search and embeddings over new entity types.
- Changes to the underlying on-disk storage layout beyond adding records for new entity and link types.
- Any broader `parse_status` refactor beyond the outcome/origin split specified in FR-002 (which IS the minimal necessary change, not a scope exception).
