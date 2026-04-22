# Data Model: Markdown ingestion produces honest, queryable results

**Feature**: `028-markdown-extraction`
**Phase**: 1 (Design)

This document captures every record shape introduced or modified by Spec-028. Field names and JSON shapes are authoritative — tasks derived by `/speckit.tasks` and tests written during implementation MUST match them.

Existing record shapes are **unchanged** and therefore not re-documented here, with exactly one exception:

- **Markdown document records** (`documents/<doc_id>.json` where `mime_type == "text/markdown"`) gain a new `text` field — see §3b. Non-markdown document records (PDF, DOCX, log, ADR, etc.) are untouched.

Everything else — chunks, sources, ADR claims, log claims, NER entities, git-provenance entities — has the same on-disk shape it had pre-028.

## 1. New entity records

All three new entity types follow the existing `entities/<shard>/<entity_id>.json` layout. The shard is the first 2 characters after the `ent_` prefix (per `auditgraph.storage.sharding.shard_dir`).

### 1.0 Entity-ID determinism (authoritative)

Every markdown sub-entity ID is computed by hashing a deterministic input string. The input string always starts with the file's `source_hash` so that (a) the same heading/token/target in two different documents produces two distinct entities and (b) any edit to the file rotates the hash and therefore the IDs (pruning per FR-016c cleans up the predecessors).

| Entity type     | Hash input (fed to `sha256_text`)                                                    | Entity ID                  |
|-----------------|---------------------------------------------------------------------------------------|----------------------------|
| `ag:section`    | `<source_hash> + "::section::" + <heading_slug_path> + "::" + <order_within_doc>`     | `ent_<sha256_text(input)>` |
| `ag:technology` | `<source_hash> + "::technology::" + <normalized_token>`                               | `ent_<sha256_text(input)>` |
| `ag:reference`  | `<source_hash> + "::reference::" + <raw_target> + "::" + <order_within_doc>`          | `ent_<sha256_text(input)>` |

The `canonical_key` **field** stored on the entity record is DIFFERENT from the ID input: `canonical_key` is the human-readable identifier used for display and graph-merge affinity (the heading slug path, the normalized token, or the raw target). The ID input is the full hash-input string above, which always scopes the hash to the originating source. The two values are not interchangeable and tests MUST NOT assume otherwise.

Slug rules (used only for `ag:section` `heading_slug_path` and the `canonical_key` field):
- Lowercase every character in the heading text.
- Replace every run of non-word characters (anything outside `[A-Za-z0-9_]`) with a single `-`.
- Strip leading and trailing `-`.
- For nested headings, join ancestor slugs with `/` (e.g., `introduction/install`).

Note: this slug rule does NOT delegate to `auditgraph.storage.ontology.canonical_key` (which is a single-string utility), despite earlier drafts of this document claiming otherwise. The slug rule is defined inline here and implemented in `auditgraph/extract/markdown.py` — do not substitute the existing `canonical_key` helper.

### 1.1 `ag:section`

```json
{
  "id": "ent_<sha256_text(id_input)>",
  "type": "ag:section",
  "name": "<verbatim heading text, redacted>",
  "canonical_key": "<lowercased-slug-joined-heading-path>",
  "aliases": [],
  "provenance": {
    "created_by_rule": "extract.markdown.section.v1",
    "input_hash": "<source_hash>",
    "pipeline_version": "<from config run_metadata>"
  },
  "refs": [
    {
      "source_path": "<as-posix path relative to workspace root>",
      "source_hash": "<source_hash>",
      "range": { "start_line": <int>, "end_line": <int> }
    }
  ],
  "body_snippet": "<first N characters of heading body, redacted>",
  "level": <int 1..6>,
  "order": <int, 0-based token-stream index>,
  "parent_section_id": "<ent_…> | null"
}
```

Constraints:

- `canonical_key` is the lowercased-slug-joined heading path (see §1.0 slug rules), e.g. `introduction/install`. The **ID** is hashed from a different, source-scoped input (see §1.0) — never confuse the two.
- `name` and `body_snippet` MUST pass through the request-scoped `Redactor` before serialization (Spec 027 FR-016).
- `parent_section_id` is resolved as **"the nearest preceding heading with strictly lower numeric heading level; otherwise `null`."** This produces deterministic behavior for every possible heading sequence:
  - H1 heading at any position → `parent_section_id = null` (no heading has a lower level).
  - Standard nesting `H1 → H2 → H3` → each heading points to its immediate parent.
  - Document starts with H2 (no H1 ever appears) → the H2's parent is `null`. Subsequent H3s under that H2 point to the H2.
  - Skipped level `H1 → H3` (no H2) → the H3's parent is the H1 directly.
  - Level drops `H1 → H2 → H3 → H2` → the second H2 has the original H1 as its parent (nearest preceding strictly-lower); the H3's parent is the first H2.
- `body_snippet` captures content between this heading and the next heading of equal or greater level; truncated deterministically at 512 chars of redacted text.
- `order` breaks ties across headings with identical text at different document positions AND feeds the ID input so two identically-named, identically-pathed headings in one document (pathological but possible) produce distinct IDs.

### 1.2 `ag:technology`

```json
{
  "id": "ent_<sha256_text(id_input)>",
  "type": "ag:technology",
  "name": "<first-occurrence verbatim token, redacted>",
  "canonical_key": "<case-folded, whitespace-trimmed token>",
  "aliases": [],
  "provenance": {
    "created_by_rule": "extract.markdown.technology.v1",
    "input_hash": "<source_hash>",
    "pipeline_version": "<from config run_metadata>"
  },
  "refs": [
    {
      "source_path": "<as-posix path>",
      "source_hash": "<source_hash>",
      "range": { "start_line": <int of first occurrence>, "end_line": <int> }
    }
  ],
  "first_seen_order": <int>,
  "origin": "<'code_inline' | 'fence'>"
}
```

Constraints:

- `canonical_key` is the case-folded, whitespace-trimmed token per Clarification Q2 (e.g., `postgresql`). This IS the per-document dedup key; two occurrences of `PostgreSQL` and `postgresql` in the same document produce **one** entity with `name` set to whichever appeared first.
- Dedup scope is **per document**. The same normalized token in two different documents produces two distinct entities because the ID input is source-scoped (see §1.0).
- `origin` records the token's source context. Allowed values: `code_inline` (inline backtick span) or `fence` (fenced code block `info` string / language tag). Per FR-016g, a fenced block emits exactly one `ag:technology` entity whose token is the `info` string; body content is NOT mined for tokens. Indented code blocks emit no `ag:technology`.
- `refs[0]` points at the first occurrence; subsequent occurrences are reachable via `mentions_technology` links from sections.

### 1.3 `ag:reference`

```json
{
  "id": "ent_<sha256_text(id_input)>",
  "type": "ag:reference",
  "name": "<link text if any, else target; redacted>",
  "canonical_key": "<redacted raw href target>",
  "aliases": [],
  "provenance": {
    "created_by_rule": "extract.markdown.reference.v1",
    "input_hash": "<source_hash>",
    "pipeline_version": "<from config run_metadata>"
  },
  "refs": [
    {
      "source_path": "<as-posix path>",
      "source_hash": "<source_hash>",
      "range": { "start_line": <int>, "end_line": <int> }
    }
  ],
  "target": "<raw href string, redacted>",
  "resolution": "<'internal' | 'external' | 'unresolved'>",
  "target_document_id": "<doc_… if resolution == 'internal', else null>",
  "order": <int, 0-based token-stream index>
}
```

Constraints:

- Classification per Clarification Q3 and FR-016f:
  - `internal`: `target` resolves (after path normalization relative to `source_path.parent`, URL-decoding, and query-string / fragment stripping) to a document already materialized at `pkg_root / "documents" / f"{doc_id}.json"` in the current run. Set `target_document_id` to that doc's ID.
  - `external`: `target` has a scheme in `{http, https, ftp, ftps, mailto}` and is not internal.
  - `unresolved`: anything else, including broken relative paths, fragment-only targets (`#anchor`), directory / bare-name targets, unsupported schemes, and malformed hrefs.
- `target` is the raw href from the markdown token (not the resolved form). Ordering & dedup are on the raw value to keep IDs stable across arbitrary resolver changes.
- `target` MUST be redacted before serialization if it contains credential-shaped content (e.g., `https://user:pass@host/...` — the vendor_token / url_credentials detectors of Spec 027 handle this).
- Bare URLs (plain-text `https://example.com` without `<>` wrapping) are captured per FR-016h because the parser adapter enables markdown-it-py's `linkify` option. Autolinks (`<url>`) are captured unconditionally.
- Images (`![alt](src)`) are ignored in v1 per FR-016g — they produce neither `ag:reference` nor `ag:technology` entities.
- `canonical_key` is the **redacted** raw href target (human-readable, written to disk). The source-scoped hash input for the entity ID is the separate string documented in §1.0 — the two MUST NOT be conflated. Per adjustments3.md §18, the ID input AND the stored `target` / `canonical_key` both use the POST-redaction target: because the extractor receives already-redacted document text, the href it sees is already scrubbed, so no credential-shaped substring can appear in IDs or on-disk strings. If the redaction policy changes, IDs rotate deterministically alongside the stored values.

## 2. New link records

All links land at `links/<shard>/<link_id>.json`. `link_id = lnk_<sha256_text(id_input)>` where the link's `id_input` is `<rule_id>::<from_id>::<to_id>`. The label `id_input` (rather than the older `canonical_key`) is used here to avoid confusion with entity records' `canonical_key` field — see §1.0 for the parallel distinction on entities.

Topology is deliberately simple and parallel (per FR-016 adjustments, §A4):

| Rule ID                                    | Link type              | From                                                      | To                  | Emitted when                  | Confidence |
|--------------------------------------------|------------------------|-----------------------------------------------------------|---------------------|-------------------------------|------------|
| `link.markdown.contains_section.v1`        | `contains_section`     | `note` (document anchor) or `ag:section` (parent)         | `ag:section`        | every emitted section         | 1.0        |
| `link.markdown.mentions_technology.v1`     | `mentions_technology`  | `ag:section` (enclosing) OR `note` (if token is before the first heading or no headings exist) | `ag:technology`     | every section/anchor that contains the token | 1.0 |
| `link.markdown.references.v1`              | `references`           | `ag:section` (enclosing) OR `note` (if link is before the first heading or no headings exist) | `ag:reference`      | every emitted reference (internal, external, or unresolved) | 1.0 |
| `link.markdown.resolves_to_document.v1`    | `resolves_to_document` | `ag:reference`                                            | `doc_<target_id>`   | reference `resolution="internal"` only | 1.0 |

Rules:

- Rule-based extraction emits confidence 1.0 because AST structure is deterministic. No NER-style quality filter.
- `contains_section` edges from a document-level anchor use the existing `ent_<note>` entity (the `note` produced by `build_note_entity`) as the "from" side. No new document-level entity is introduced.
- Every `ag:reference` entity — regardless of resolution — receives one `references` edge from its enclosing section. External and unresolved references emit no second edge; their classification is carried on the reference entity's `resolution` field, not in graph topology.
- Only internal references also emit a `resolves_to_document` edge from the reference entity to the target `doc_…` record. This is the sole edge in the graph that terminates at a non-entity node (documents are not registered as entities per spec-028 scope).

## 3. Modified record: `IngestRecord`

**Before** (`auditgraph/storage/manifests.py`, current):

```json
{
  "path": "...",
  "source_hash": "...",
  "size": 123,
  "mtime": 1700000000.0,
  "parser_id": "text/markdown",
  "parse_status": "ok | failed | skipped",
  "status_reason": "...",
  "skip_reason": "..."
}
```

**After** (Spec-028):

```json
{
  "path": "...",
  "source_hash": "...",
  "size": 123,
  "mtime": 1700000000.0,
  "parser_id": "text/markdown",
  "parse_status": "ok | failed | skipped",
  "status_reason": "...",
  "skip_reason": "...",
  "source_origin": "fresh | cached"
}
```

Semantic split:

- `parse_status` now strictly describes **parse outcome** for this record. Values:
  - `ok` — parse completed successfully (whether fresh or from cache).
  - `failed` — parse was attempted and failed; file is excluded from downstream stages.
  - `skipped` — file was not parsed for a structural reason (unsupported extension, symlink refused). Downstream stages exclude these.
- `source_origin` describes **execution origin**:
  - `fresh` — parsed during this run.
  - `cached` — document and chunk records were already on disk with matching `source_hash`; parse was not re-executed.

Downstream filters (`run_extract`, indexers) use `parse_status == "ok"` regardless of `source_origin`.

### Backward-compat reader

Before filtering, `run_extract` passes the loaded ingest manifest through a normalizer:

- Any record with `parse_status == "skipped"` **AND** `skip_reason in {"unchanged_source_hash", SKIP_REASON_UNCHANGED}` is rewritten in memory to `parse_status="ok"`, `source_origin="cached"`.
- All other records unchanged.

The normalizer is pure (no disk writes). It lets pre-028 workspaces' existing manifests feed the post-028 extract stage without a rebuild.

## 3a. Known storage-form deviation: absolute `source_path` on documents/chunks

**Status**: known gap, not blocking. Tracked for a follow-up spec.

The data-model contract calls for `source_path` values to be stored in
**normalized workspace-relative POSIX form** across `documents/`,
`chunks/`, `sources/`, `entities/`, and `links/` artifacts. The current
implementation of `auditgraph/ingest/parsers.py :: _build_document_metadata`
stores the **absolute path** for `document.source_path`, `chunk.source_path`,
and uses the absolute path as the input to
`deterministic_document_id(path, source_hash)`.

Downstream consumers tolerate this today:

- `DocumentsIndex` is built from `source_hash` joins — not from path
  comparison — so the relative-vs-absolute mismatch does not leak into
  reference classification.
- `entity.refs[0].source_path` is set to the workspace-relative form by
  the extract-stage entity builders (which receive `source_path` from
  the normalized ingest record).
- `node_view` and query commands display `source_path` as-is — either
  form is readable.

Fixing this would require a one-time document-ID migration (old absolute-
hash IDs → new relative-hash IDs). That migration is out of scope for
spec-028 and would be its own spec.

Tests that assert on stored `source_path` should use substring matching
rather than equality when cross-workspace portability matters.

## 3b. Modified record: `document` payload

Before (existing `auditgraph/ingest/parsers.py :: _build_document_metadata`):

```json
{
  "document": {
    "document_id": "...",
    "source_path": "...",
    "source_hash": "...",
    "mime_type": "text/markdown",
    "file_size": 1234,
    "extractor_id": "...",
    "extractor_version": "...",
    "ingest_config_hash": "...",
    "status": "ok",
    "status_reason": null,
    "hash_history": ["..."]
  },
  "segments": [...],
  "chunks": [...]
}
```

After (Spec-028, per FR-015a):

```json
{
  "document": {
    "document_id": "...",
    "source_path": "...",
    "source_hash": "...",
    "mime_type": "text/markdown",
    "file_size": 1234,
    "extractor_id": "...",
    "extractor_version": "...",
    "ingest_config_hash": "...",
    "status": "ok",
    "status_reason": null,
    "hash_history": ["..."],
    "text": "<redacted full markdown text as parsed by the markdown backend>"
  },
  "segments": [...],
  "chunks": [...]
}
```

Constraints:

- `text` is REQUIRED on every markdown document record written by a Spec-028-or-later ingest run. For `mime_type != "text/markdown"`, the field is absent (NOT null) to keep non-markdown document payloads byte-identical to pre-028.
- `text` has already passed through the request-scoped `Redactor` at parser entry (Spec 027 FR-016). No second redaction occurs when the extractor reads the field.
- `text` is used as the input to `extract_markdown_subentities`. The extractor MUST NOT re-read source files from disk; this field is the single path from ingest redaction to sub-entity extraction.
- Adding the field preserves `outputs_hash` determinism because identical inputs produce identical redacted text.
- **Cache completeness (FR-016b1)**: When the ingest stage encounters a cache hit for a markdown source (source_hash matches an on-disk `documents/<doc_id>.json`) but the cached record LACKS the `text` field, it MUST treat the cache as incomplete for that source, reparse and redact the source once, and rewrite the document record with `text`. This is the one-time migration path for pre-028 workspaces. Subsequent runs see the refreshed record and take the normal cache-hit path.
- The extract stage MUST NOT tolerate a missing `text` field on a markdown document record. If one is encountered, this is an ingest-stage bug — surface an explicit error rather than silently producing zero sub-entities.

## 4. Modified record: `StageManifest`

```json
{
  "version": "v1",
  "schema_version": "<unchanged>",
  "stage": "extract | index | ingest | ...",
  "run_id": "...",
  "started_at": "<deterministic ISO8601>",
  "finished_at": "<deterministic ISO8601>",
  "wall_clock_started_at": "<ISO8601 UTC wall-clock>",
  "wall_clock_finished_at": "<ISO8601 UTC wall-clock>",
  "inputs_hash": "...",
  "outputs_hash": "...",
  "config_hash": "...",
  "status": "ok | missing_manifest | ...",
  "artifacts": ["..."],
  "warnings": [
    { "code": "no_entities_produced", "message": "extract produced 0 entities from 17 inputs", "hint": "Enable NER, add rule packs, or verify parsers emit entities." }
  ]
}
```

Three new fields, all additive:

- `wall_clock_started_at`, `wall_clock_finished_at`: UTC ISO-8601, never participate in `outputs_hash`.
- `warnings`: list of structured advisory records. Empty list when no warnings. Never participates in `outputs_hash`.

### IngestManifest

Same three new fields with identical semantics. Existing aggregate counters (`ingested_count`, `skipped_count`, `failed_count`) are unchanged. New optional counter `cached_count: int` may be derived from records at manifest build time for observability; it is additive.

## 5. Entity state transitions and pruning

Sub-entities have no complex state machine. The lifecycle is:

1. Ingest parses the source file and persists the redacted full markdown text on the `document` record (FR-015a — a new `text` field on `documents/<doc_id>.json`).
2. Extract reads the `document.text` field, feeds it to the markdown walker, and collects emitted entities + links.
3. Each emitted string field passes through the request-scoped `Redactor` as a defense-in-depth check.
4. Deterministic ID computed from source-scoped hash input (see §1.0).
5. Entity dicts collected in a per-document dict keyed by ID (natural dedup for technology tokens).
6. **Pruning** (per FR-016c). Link records do NOT carry a `source_path` field — links only carry `from_id`, `to_id`, `type`, and `rule_id`. The algorithm therefore prunes links via the entity IDs they reference:

   **Pruning algorithm** (runs once per source being re-extracted, before writing refreshed sub-entities):

   a. Enumerate every on-disk entity file under `entities/<shard>/` whose record satisfies ALL of:
      - `type ∈ {"ag:section", "ag:technology", "ag:reference"}`, AND
      - `refs[0].source_path == <current_source_path>`.
   Collect their IDs into a set `stale_entity_ids`.

   b. Delete every entity file in `stale_entity_ids`.

   c. Enumerate every on-disk link file under `links/<shard>/` and delete those that satisfy ALL of:
      - `rule_id ∈ {"link.markdown.contains_section.v1", "link.markdown.mentions_technology.v1", "link.markdown.references.v1", "link.markdown.resolves_to_document.v1"}`, AND
      - `from_id ∈ stale_entity_ids` OR `to_id ∈ stale_entity_ids`.

   The `from_id in stale_entity_ids` check catches `contains_section` edges (where the from-side is a note entity, whose ID is not in the set) by also matching the `to_id` — the section (to-side) IS in `stale_entity_ids`. This is why the filter is `from OR to` rather than just `from`.

   Only one edge type in the set terminates outside markdown sub-entities: `resolves_to_document`'s `to_id` is a `doc_…` ID, never in `stale_entity_ids`. But its `from_id` IS in `stale_entity_ids` (it's an `ag:reference`), so the `from` branch of the filter catches it.
7. The refreshed per-document entity list and link list are unioned across all markdown sources in the run and written via the existing `write_entities` / `write_links` helpers.

Pruning is scoped STRICTLY to the four markdown-sub-entity link rule IDs and the three markdown-sub-entity types (per FR-016d). Other entity types (`note`, any `ner:*`, `commit` / `author` / `file` / `repo` / `tag` / `ref` git-provenance records, or any user-introduced type) are NEVER deleted by this mechanism. Links produced by the generic source-cooccurrence rule (`link.source_cooccurrence.v1`) are also untouched — they are type-filtered to exclude markdown sub-entities entirely per FR-016e.

Documents for which no source record remains in the current ingest manifest are NOT pruned by this spec. Cross-source garbage collection (orphan-document cleanup) is out of scope and would need its own spec.

## 6. Invariants

These invariants MUST hold and MUST be expressed as test assertions:

- **I1 (ID determinism)**: For any fixed source markdown file, the set of emitted entity IDs and link IDs is a pure function of the file's bytes and the pipeline's `config_hash`. Two runs against the same input produce byte-identical entities and links on disk.
- **I2 (Redaction completeness)**: No entity or link record written to disk contains a credential-shaped string that passes any Spec-027 detector. Asserted end-to-end via the existing postcondition test harness on a fixture containing seeded secrets.
- **I3 (Reference consistency)**: For every `ag:reference` with `resolution == "internal"`, (a) the `target_document_id` MUST point at a `documents/<doc_id>.json` file that exists on disk in the same run's profile store, AND (b) a `link.markdown.resolves_to_document.v1` edge MUST exist from the reference entity to that document. For every `ag:reference` with `resolution ∈ {"external", "unresolved"}`, no `resolves_to_document` edge MUST exist.
- **I9 (Pruning correctness)**: After any extract run against a source whose content changed, the entity store MUST NOT contain any `ag:section` / `ag:technology` / `ag:reference` entity whose primary source reference matches the source path with a pre-change `source_hash`. Asserted by diffing entity sets before and after a controlled edit in a fixture test.
- **I10 (Cooccurrence exclusion)**: For every `link.source_cooccurrence.v1` link written to disk, NEITHER its `from_id` NOR its `to_id` MUST identify an entity of type `ag:section`, `ag:technology`, or `ag:reference`. This is the EITHER-endpoint rule (per FR-016e and adjustments3.md §15) — a link with one markdown endpoint and one non-markdown endpoint is ALSO a violation, not just same-type pairs. Asserted by inspecting the written links index after a full pipeline run on a markdown corpus.
- **I4 (Technology dedup scope)**: For any fixed document, the set of `ag:technology` entities has unique `canonical_key` values. Cardinality equals the number of distinct case-folded, whitespace-trimmed code tokens in the document.
- **I5 (Section parent chain)**: For every `ag:section` with `parent_section_id != null`, the parent entity exists in the same run's profile store. No dangling parent pointers.
- **I6 (Parse status/origin orthogonality)**: For every ingest record, `parse_status ∈ {ok, failed, skipped}` and `source_origin ∈ {fresh, cached}`. `parse_status == "failed"` implies `source_origin == "fresh"` (a parse must be attempted before it can fail). `source_origin == "cached"` implies `parse_status == "ok"` (a cache hit means we previously parsed successfully).
- **I7 (Wall-clock independence)**: The `outputs_hash` computed on any stage manifest is the same whether `wall_clock_*` fields carry real timestamps or placeholder values. Asserted by running the full pipeline twice and diffing `outputs_hash`.
- **I8 (Warning persistence)**: When `warnings` is non-empty in a live `StageResult`, the same list MUST appear in the persisted stage manifest on disk. No CLI-only warnings.
