# External consumer report — auditgraph v0.1.0 findings

**Reporter context:** diagnostic feedback from an external consumer project
running `auditgraph run` against a plain-markdown documentation corpus (~17
`.md` files, ~387 chunks, no ADRs, no log files, NER disabled). The pipeline
reports success at every stage but produces 0 queryable entities. This report
catalogs the bugs surfaced during that diagnosis and proposes a spec for
the capability gap underneath.

**Scope:** auditgraph only. No consumer-side integration notes.

**File references use** `auditgraph/auditgraph/...` for source paths and
`auditgraph/config/...` for shipped config.

---

## 1 · Bug reports

### BUG-1 · Cache-skip starves `run_extract` of inputs

**Severity:** High — observable failure mode: 0 entities from N valid inputs.

**Where:** `auditgraph/pipeline/runner.py`
- Filter at line 570 and 577: `if record.get("parse_status") != "ok": continue`
- Ingest manifest produced by a prior (or same-run) execution marks cached
  records as `parse_status: "skipped"` with `skip_reason:
  "unchanged_source_hash"`.

**Observed.** After a fresh `auditgraph init` + `auditgraph ingest` (17 ok)
+ `auditgraph run`, the extract stage's own manifest reports `artifacts: []`
and `outputs_hash` corresponds to empty entity/claim sets. The
`build_note_entity` call site at `runner.py:591` is inside the filtered
loop, so it runs zero times on rerun. Documents are materialized under
`.pkg/profiles/<p>/documents/` but nothing reaches `.pkg/profiles/<p>/entities/`
— that directory isn't even created.

**Hypothesis.** The status field conflates two orthogonal concepts:
1. *Parse outcome* — did this file parse correctly? (`ok`/`failed`)
2. *Execution origin* — did we parse fresh or reuse cached output?
   (`fresh`/`cached`)

Today both get stuffed into `parse_status`, so `cached` looks like
`skipped`, and downstream stages treat `skipped` as "don't process." But
cached data is perfectly valid input — the source JSON and chunks are
already on disk.

**Proposed fix (choose one):**

- **(a) Separate the concepts.** Keep `parse_status ∈ {ok, failed}` as the
  correctness signal. Add a new `source_origin ∈ {fresh, cached}` for
  cache telemetry. Update downstream filters to use `parse_status == "ok"`
  regardless of origin. Minimal change to the canonical contract; all
  cached files correctly participate in later stages.
- **(b) Treat cache hits as a first-class success.** In ingest, emit
  `parse_status: "ok"` with `skip_reason: "unchanged_source_hash"` when a
  cache hit occurs. This preserves the existing downstream filter but
  reinterprets `skipped` to mean "genuinely did not parse" (e.g., unsupported
  extension), not "cache hit."

Option (a) is cleaner and more honest to the manifest contract.

**Repro (from a clean workspace, markdown content only):**

```bash
auditgraph init --root .
# add some .md files under one of the include_paths
auditgraph run
# inspect: .pkg/profiles/default/runs/<run>/extract-manifest.json
# expect: artifacts = []
# expect: no .pkg/profiles/default/entities/ directory
auditgraph list --count   # returns 0
auditgraph query --q "<any word from content>"   # returns []
```

---

### BUG-2 · Orphan `rule_packs` references in shipped default config

**Severity:** Medium — silent misconfiguration, user-hostile.

**Where:** `auditgraph/config/pkg.yaml`
- Line 57-58: `extraction.rule_packs: ["config/extractors/core.yaml"]`
- Line 109-110: `linking.rule_packs: ["config/link_rules/core.yaml"]`

Neither path exists in the shipped repo (`config/extractors/` and
`config/link_rules/` are empty directories). The pipeline runs to
completion without warning that the referenced rule packs are missing.

**Impact.** Users who do not read the full source tree have no visible
signal that their extraction/linking is running with zero rules. Combined
with BUG-1 and BUG-5 this produces a confidently silent "successful"
empty pipeline.

**Proposed fix (choose one or both):**

1. **Ship a minimal `core.yaml`** for each. Even a well-commented empty
   file with a schema version is better than a missing one.
2. **Fail-loud on missing rule pack paths.** The config loader should
   resolve `rule_packs` at startup and emit a clear error (or at least
   a structured warning) when a declared path cannot be read.

Both are cheap. (1) is the user-facing fix, (2) is the hardening.

---

### BUG-3 · Placeholder timestamps leak into production manifests

**Severity:** Low — cosmetic, but undermines audit trust.

**Where:** Every stage manifest under
`.pkg/profiles/<p>/runs/<run>/*.json`.

**Observed.** Real-world runs carry `started_at` and `finished_at` values
of `"1995-12-23T04:33:39Z"`. This is clearly a fixed deterministic
placeholder, not an actual wall-clock time.

**Likely cause.** A determinism-test fixture time is being substituted
into the manifest writer unconditionally, probably via a patched `now()`
or an env var intended for the test suite that defaults on in the
production code path.

**Proposed fix.** Keep wall-clock timestamps in a `wall_clock_started_at`
/ `wall_clock_finished_at` field; keep the deterministic placeholder only
for the fields that feed `outputs_hash` (where reproducibility matters).
Never substitute wall-clock for deterministic in non-test code paths.

---

### BUG-4 · `auditgraph node <document_id>` looks up in the wrong shard

**Severity:** Medium — first-class navigation command fails on a
first-class artifact class.

**Where:** `auditgraph/auditgraph/` wherever `node` is dispatched
(subcommand handler for `node`).

**Observed.**
```
$ auditgraph node doc_8117457eaecc24b8a1f5bb31
{
  "status": "error",
  "message": "[Errno 2] No such file or directory:
   '.../entities/81/doc_8117457eaecc24b8a1f5bb31.json'"
}
```

Documents live under `documents/<doc_id>.json`, not
`entities/<shard>/<doc_id>.json`. The ID-prefix pattern (`doc_`, `chk_`,
`ent_`, etc.) carries the type signal; the lookup should dispatch
accordingly.

**Proposed fix.** Add ID-prefix dispatch in the `node` resolver:
- `doc_*` → `.pkg/profiles/<p>/documents/<id>.json`
- `chk_*` → `.pkg/profiles/<p>/chunks/<shard>/<id>.json`
- `ent_*` / `note_*` → `.pkg/profiles/<p>/entities/<shard>/<id>.json`
- Fallback: scan all three before erroring.

Alternative: promote documents to full entity status (register them in
`entities/`). This is a larger change and overlaps with BUG-5 / spec-028.

---

### BUG-5 · Empty pipeline returns `status: ok` without warning

**Severity:** Medium — silent failure mode; combines with BUG-1 to make
the problem undiagnosable without source reading.

**Where:** `pipeline/runner.py::run_extract` and `run_index`, and the
`run` aggregator.

**Observed.** 17 ingested markdown files → 17 documents → 387 chunks →
0 entities → empty BM25 index → `{"status": "ok"}` at every stage. The
redaction postcondition passes (correctly — there are no secrets), which
further cements the false-success signal.

**Proposed fix.** A lightweight postcondition that compares pipeline
throughput ratios:

- If `ingest.ok > 0` and `extract.entities_written == 0`, emit a
  structured `status: "no_entities"` or at minimum a WARN in the manifest
  and the CLI JSON:
  ```json
  { "stage": "extract", "status": "ok",
    "warnings": [{"code": "no_entities_produced",
                   "hint": "Enable NER, add rule packs, or check that
                            ingested parsers emit entities."}] }
  ```
- If `extract.entities_written > 0` and `index.bm25_entries == 0`,
  emit `empty_index` WARN.

This is the smallest intervention that converts the silent failure into
a loud one without changing exit codes.

---

## 2 · Capability gap — proposed spec-028

### 2.1 · The gap

`auditgraph/CLAUDE.md` states:

> Markdown sub-entity extraction (`ag:section`, `ag:technology`,
> `ag:reference`) is planned but not enabled in the default pipeline yet.

Today the only entity producers in the extract stage are:

- ADR claim extraction (`extract/adr.py`)
- Log claim extraction (`extract/logs.py`)
- NER (`extract/ner.py`) — off by default, quality known-poor on
  technical content (per auditgraph's own CLAUDE.md)
- `build_note_entity` — one `note` entity per markdown file (present in
  code; currently starved by BUG-1)

A plain-markdown documentation workspace therefore yields at most `N`
note-level entities and no sub-document structure. Queries over section
titles, inline code, or cross-document references are impossible. This
is the single biggest capability gap for the most common ingestion
target (developer documentation).

### 2.2 · Proposal: spec-028 — Markdown sub-entity extraction

**Status:** proposed. Not yet filed.

**Goal.** Deterministic, model-free extraction of markdown sub-document
entities so that BM25 and graph queries produce meaningful results on
any markdown workspace without enabling NER.

**Sub-entity types to emit:**

| Type | Source token | Emits per |
|---|---|---|
| `ag:section` | ATX / Setext heading | heading; hierarchical via `parent_section_id`; body text captured |
| `ag:technology` | Inline ``code`` spans, fenced code blocks | distinct token (deduplicated per-doc) |
| `ag:reference` | `[text](url)`, reference-style links, bare URLs | link; target resolved where local |

**Producer module.** New file: `auditgraph/extract/markdown.py`. Parses
via `markdown-it-py` (already present as a transitive dep per
`port.yaml` in the installed tree). Walks the token stream; builds an
AST section tree; emits entities and links.

**Wiring.** `pipeline/runner.py::run_extract`, inside the `if parser_id
== "text/markdown":` branch (around line 583-592), after the existing
`build_note_entity` call:

```text
markdown_entities, markdown_links = extract_markdown_subentities(
    source_path, source_hash, chunk_records, redactor=redactor
)
for ent in markdown_entities:
    entities[ent["id"]] = ent
markdown_link_paths = write_links(pkg_root, markdown_links)
```

(This parallels the existing NER branch 20 lines down.)

**Link types (additions to `config/link_rules/core.yaml` once BUG-2 is
resolved):**

- `contains_section` — note → section, section → section (parent/child)
- `mentions_technology` — section → technology
- `references_document` / `references_external` — section → (document | url)

**Entity ID determinism.**

- `ag:section`: `sha256(source_hash || heading_path_index_slug || order)[:24]`
- `ag:technology`: `sha256(source_hash || normalized_token)[:24]`
- `ag:reference`: `sha256(source_hash || link_target || order)[:24]`

No timestamps, no runtime state, no Python object IDs. Two runs against
the same source must produce identical IDs and identical link sets.

**Index updates.**

- `index/bm25.py::build_bm25_index` — ensure text fields (`section.title`,
  `section.body_snippet`, `technology.token`) are indexed.
- `index/types.py` (Spec 023) — register new type facets so
  `auditgraph list --type ag:section` / `--type ag:technology` work.

**Test contract.**

- Fixture markdown exercising: H1–H6, nested headings, fenced + inline
  code, three link styles, frontmatter, embedded secrets.
- Unit test per producer: stable-ID regression.
- Pipeline test: run twice against fixture, assert identical
  `outputs_hash` on extract + index manifests.
- Redaction test: secrets in section bodies must be redacted before
  entity write (Spec 027 FR-016 compliance).

**Config.** No new config required; the producer runs unconditionally
for any `parser_id == "text/markdown"`. (Future: spec-024 could gate it
on document class — see §3.)

**Out of scope for spec-028:**

- Model-based entity extraction (spec 024, spec 018 domain).
- PDF / DOCX sub-entity extraction — same pattern, different noise
  profile; should be a separate spec once 028 validates the approach.
- Semantic search / embeddings (spec 019 domain).

**Shipping.** Additive-minor. Existing workspaces would run `auditgraph
rebuild` to pick up new entity types. CHANGELOG + QUICKSTART + CLAUDE.md
updates; flip the "planned but not enabled" sentence.

---

## 3 · Relationship to spec-024

Spec-024 (*Document Classification & Dynamic Model Selection*,
pre-spec NOTES.md dated 2026-04-07) and this spec-028 proposal address
adjacent but **orthogonal** concerns.

### 3.1 · What each addresses

**Spec-024:** *Which model should run against each document?*
- Per-document parser selection beyond extension-routing.
- Per-document NER model selection (e.g., `en_core_sci_sm` for research
  papers, domain models for legal, none for code-dominant files).
- Per-document noise stripping (markdown vs PDF vs plain text).

**Spec-028 (proposed):** *What structural entities should we extract
from markdown, model-free?*
- Deterministic rule-based sub-entity production.
- No model dependency, no classification required to run.
- Only active when `parser_id == "text/markdown"` (a signal already set
  by today's extension router).

### 3.2 · Interaction points

1. **Activation gating.** Today, extension routing (`.md` → `text/markdown`)
   is the only signal spec-028 needs. Once spec-024 ships document
   classification, spec-028 could optionally gate on classification:
   e.g., run sub-entity extraction on `documentation` / `research` /
   `note` document classes, skip on `code-dump` or `log-export` classes
   even if they're technically `.md`. This is a refinement, not a
   prerequisite.

2. **Quality filter composition.** Spec-024's NER-quality work (Issue 3
   Phase 3 already partially shipped; see `extract/ner.py::filter_low_quality_entities`)
   filters false positives from `en_core_web_sm`. Spec-028 produces
   rule-based entities that *don't need* quality filtering — their
   precision comes from AST structure. Running both in the same pipeline
   is fine; filters don't overlap.

3. **Noise stripping.** Spec-024's pre-spec notes call out a markdown
   noise stripper (Issue 3 Phase 2) for chunk-level NER input. Spec-028
   operates on the *original* markdown AST, not the noise-stripped chunk
   text — so it is not affected by whatever markdown normalization
   spec-024 introduces. They share a dependency on markdown-it-py (or
   equivalent) but call into it independently.

### 3.3 · Ordering — which ships first?

The cases are non-trivial. Presented without a recommendation:

**Case for spec-024 first:**

- Larger refactor; it's architecturally cleaner to land the
  classification framework before bolting new extractors onto it.
- Spec-028 could then register itself as a classifier-gated producer
  from day one rather than being migrated later.
- Spec-024 addresses NER quality, which is the #1 reported quality
  issue on technical content. Unblocking that widens the tool's useful
  scope for every content type, not just markdown.
- spec-028 is a leaf capability; spec-024 is a cross-cutting change.

**Case for spec-028 first:**

- Spec-028 is simpler: rule-based, no model selection, no new
  dependencies, no download-time cost.
- Spec-028 directly addresses the observable failure mode (empty BM25
  on markdown workspaces). A user's first run is a markdown run;
  spec-028 makes that run useful immediately.
- Spec-024 is still at pre-spec NOTES.md stage (Status:
  "NOT ready for `/speckit.specify`"). Its scope is not yet converged
  and may take multiple cycles; spec-028 is fully scopable today.
- No refactor of spec-028 is required once spec-024 lands — a
  classification gate is a one-line addition to the producer's activation
  condition.

**Blocking relationship:** none. Spec-028 can ship without spec-024; the
reverse is also true. The two are independent capability increments.

### 3.4 · Prerequisites (both specs)

Regardless of ordering, the bugs in §1 should land first:

- **BUG-1** is a prerequisite for *any* extract-stage work. Without the
  fix, spec-028's new producers would be starved by the same cache filter
  that starves `build_note_entity` today.
- **BUG-2** is a prerequisite for the `config/link_rules/core.yaml`
  additions that spec-028 needs.
- **BUG-5** converts silent-success regressions into loud ones and
  should be in place before landing new entity producers.

BUG-3 and BUG-4 are independent polish.

---

## 4 · Recommended decision sequence

The pragmatic path forward within auditgraph is:

1. Fix BUG-1 (cache-skip) — unblocks `build_note_entity` and any future
   extract producer.
2. Fix BUG-2 (rule-pack orphan) and BUG-5 (empty-pipeline warning) —
   eliminate silent misconfiguration.
3. Decide spec-024 vs spec-028 ordering based on maintainer bandwidth:
   - If a larger design cycle is acceptable: spec-024 first, then
     spec-028 slots in as a classifier-gated producer.
   - If shipping observable value quickly matters: spec-028 first as a
     standalone rule-based producer; spec-024 follows on its own cadence.
4. Fix BUG-3 and BUG-4 opportunistically alongside the above.

Both specs unlock use cases that today are functionally impossible on
the default pipeline. The bugs in §1 are preconditions regardless of
which spec lands first.

---

## Appendix A · Evidence pointers

- `auditgraph/pipeline/runner.py:570,577` — parse_status filter
- `auditgraph/pipeline/runner.py:591` — existing `build_note_entity` call
- `auditgraph/pipeline/runner.py:603-627` — NER branch, pattern to mirror
  for spec-028
- `auditgraph/config/pkg.yaml:57-58,109-110` — rule_pack orphan paths
- `auditgraph/CLAUDE.md` (in repo root) — "planned but not enabled"
  sentence for markdown sub-entity extraction
- `auditgraph/specs/024-document-classification-and-model-selection/NOTES.md`
  — spec-024 pre-spec capture
- `auditgraph/extract/` — module layout (sibling of `adr.py`, `logs.py`,
  `ner.py` where spec-028's `markdown.py` would live)
