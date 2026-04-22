# Research: Markdown ingestion produces honest, queryable results

**Feature**: `028-markdown-extraction`
**Phase**: 0 (Research) — resolves every NEEDS CLARIFICATION from Technical Context

This document captures the seven research threads that had to converge before writing the plan. Each thread ends with a **Decision**, **Rationale**, and **Alternatives considered**. Evidence (file paths and line numbers) is cited inline.

---

## R1. Markdown parser choice

**Question.** Which markdown parser gives us a deterministic AST/token stream we can walk to extract `ag:section` / `ag:technology` / `ag:reference` entities, without adding compiled dependencies?

**Investigation.**

- `markdown-it-py` 3.0.0 is already installed in the development environment as a transitive dependency of `rich` (`Required-by: rich` per `pip show markdown-it-py`). Source: `/home/socratesone/anaconda3/lib/python3.10/site-packages/markdown_it/`.
- It is **not** declared in `pyproject.toml` — the current declared deps are `pyyaml`, `neo4j`, `pypdf`, `python-docx`, `spacy`, `dulwich`, `jsonschema` (`pyproject.toml:22-30`). Relying on transitive installation is brittle.
- Candidates:
  - `markdown-it-py` — pure Python, CommonMark-compliant, exposes a token stream via `MarkdownIt().parse(text)`. MIT-licensed. Well-maintained; used by `mdit-py-plugins`, `myst-parser`, and `rich`.
  - `mistune` — faster but less canonical, smaller ecosystem, AST API has changed shape across versions.
  - `commonmark` — original Python port, effectively unmaintained since 2019.
  - `Python-Markdown` — outputs HTML only; would require HTML re-parsing to recover structure. Wrong abstraction level.

**Decision.** Declare `markdown-it-py[linkify]>=4,<5` in `pyproject.toml`'s `dependencies` (the `[linkify]` extra pulls in `linkify-it-py>=2,<3`) and use it through a thin adapter in `auditgraph/extract/markdown.py`. Token stream (`MarkdownIt("commonmark", {"linkify": True}).enable("linkify").parse(text)` — authoritative per `contracts/markdown-subentities.md` "Parser configuration" section) preserves type tags (`heading_open`, `inline`, `code_inline`, `fence`, `link_open`, `link_close`, `text`) with stable ordering — ideal for a deterministic walk. BOTH the constructor option AND the `.enable("linkify")` rule activation are required; either alone is a silent no-op.

**Critical detail re linkify.** Calling `.enable("linkify")` WITHOUT `linkify-it-py` installed is a silent no-op — `MarkdownIt` accepts the call but produces no link tokens for bare URLs, and emits no warning. Empirically verified against the current dev environment: a plain `https://example.com` in prose stays a text run when `linkify-it-py` is absent. The `[linkify]` extra is therefore non-optional for FR-016h to hold. An alternative (adding `linkify-it-py>=2,<3` as a separate root dep) is equivalent and acceptable if your dependency manager dislikes extras syntax.

**Version note.** Initial draft of this plan proposed `>=3,<4`, but the repository's `uv.lock` already resolves `markdown-it-py==4.0.0` (via `rich`). The 3.0 → 4.0 upgrade kept the public token-stream API stable — `MarkdownIt().parse(text)` returns the same token types with the same attribute shape. Pinning `>=4,<5` matches the lockfile, avoids an unnecessary downgrade, and keeps us on the actively-maintained major line.

**Rationale.**
- Already installed (so this is a declaration promotion, not a new download).
- Pure Python → no compiled deps → no wheel matrix cost.
- Deterministic AST → required by FR-011 for byte-identical reruns.
- MIT license → compatible with existing MIT codebase.
- Used by `rich` (already a deep indirect dep) → no incremental supply-chain risk.

**Alternatives considered.**
- `mistune`: rejected for API churn and for not being already present.
- `commonmark`: rejected for maintenance status.
- Hand-rolled regex parser: rejected — re-implements a solved problem, loses comment/code-fence fidelity, guarantees footguns on nested structures.

---

## R2. BUG-1 root cause and fix path for cache-starved extract

**Question.** Where exactly does the "cached file → dropped from extract" regression enter, and what is the smallest fix that separates "parse outcome" from "execution origin" without a schema bump?

**Investigation.**

- Filter site confirmed: `auditgraph/pipeline/runner.py:577` (`if record.get("parse_status") != "ok": continue`) and a second identical filter at line 570 in the `ok_paths` list comprehension.
- The `parse_status` is set at ingest time at `auditgraph/pipeline/runner.py:169`:

  ```python
  if existing_document_path.exists():
      existing_document = read_json(existing_document_path)
      if str(existing_document.get("source_hash", "")) == source_hash:
          record, metadata = build_source_record(
              path, root, parser_id_for(path),
              "skipped",                              # ← BUG: cached ≠ skipped
              status_reason=SKIP_REASON_UNCHANGED,
              skip_reason=SKIP_REASON_UNCHANGED,
          )
  ```

- `build_source_record` writes the string through to both `IngestRecord.parse_status` and the serialized JSON (`auditgraph/ingest/sources.py:29,39`).
- Record shape today is a frozen dataclass (`auditgraph/storage/manifests.py`); adding a field is mechanical.
- Clarification Q-A resolved the shape: keep `parse_status ∈ {ok, failed}`, add orthogonal `source_origin ∈ {fresh, cached}`.

**Decision.** Implement Option (a) from the Orpheus report, with a backward-compatible reader:

1. Add field `source_origin: str` to `IngestRecord` with default `"fresh"`.
2. When a cache hit occurs (`runner.py:164`), set `parse_status="ok"`, `source_origin="cached"`, keep `skip_reason=SKIP_REASON_UNCHANGED` for observability only (it no longer gates downstream).
3. In `run_extract` (both filter sites), the condition `record.get("parse_status") != "ok"` now correctly admits cached records.
4. **Backward-compat reader**: before filtering, normalize legacy ingest manifests by translating `parse_status="skipped"` + `skip_reason in {"unchanged_source_hash", SKIP_REASON_UNCHANGED}` → `parse_status="ok"` + `source_origin="cached"`. This lives in one helper (`_normalize_ingest_records`) called at the top of `run_extract`. Users with pre-028 `.pkg/profiles/...` directories get FR-016a behavior automatically on the next run.

**Rationale.**
- Honors the manifest contract: `parse_status` means "did it parse?", `source_origin` means "was it parsed this run?". No two concepts share a field.
- Backward-compat reader eliminates the need for a full rebuild; FR-016a is satisfied by existing extract behavior (which re-runs every invocation — see R4).
- Same change pattern Spec 027 used for FR-023a (env-agnostic strict-mode read) — reader tolerance at the boundary, strict producer.

**Alternatives considered.**
- Option (b) from the report (keep `parse_status="ok"` for cache hits, let `skip_reason` disambiguate): conflates outcome and origin in the reader's head and leaves `skipped` meaning different things depending on `skip_reason` content. Rejected for readability.
- Schema version bump: unnecessary — adding a field with a default is additive, per Spec 027's precedent of adding `redaction_postcondition` to `index-manifest.json` with no bump.
- Run-migration script that rewrites old manifests on disk: gratuitous destructive change to existing data. Rejected.

---

## R3. Markdown parser → entity mapping semantics

**Question.** What token sequences produce which entity classes, and what are the exact ID-generation inputs so two runs collide on the same ID?

**Investigation.**

- `markdown-it-py` token stream emits: `heading_open`/`inline`/`heading_close` triples for ATX headings; `paragraph_open`/`inline` for body text; `code_inline` nested inside `inline.children` for backtick spans; `fence` (fenced code block) as a top-level token with `info` (language) and `content`; `link_open`/`link_close` with `href`/`title` attributes inside inline children. Setext headings (`===`/`---`) normalize to the same `heading_open` tokens via CommonMark spec.
- Technology deduplication rule per Clarification Q2: case-fold (Python `str.casefold()`) + strip leading/trailing whitespace only.
- Reference classification rule per Clarification Q3: internal iff target resolves to a `documents/<doc_id>.json` present in the profile store **for this run**. External iff URL scheme is `http`/`https`/`ftp`. Unresolved iff neither.
- ID determinism pattern in the existing codebase: `ent_<sha256_text(key)>` (`auditgraph/storage/hashing.py:entity_id`) or a type-scoped variant. The existing helper happens to take a `canonical_key` string as input — for existing `note` and `ner:*` entities the canonical key IS the hash input. Spec-028 decouples the two concepts (the `canonical_key` field is human-readable; the hash input is source-scoped). Reports mentions `sha256(source_hash || content || order)[:24]` — this truncation differs from the existing 64-char hex. To stay consistent with existing entities, IDs follow the full-SHA pattern, not truncated.

**Decision.**

Entity-ID inputs (all deterministic, all rooted in the immutable source hash). The column labelled "hash input" is the string fed to `sha256_text` to produce the entity ID. This is DISTINCT from the stored `canonical_key` field on the entity — see `data-model.md §1.0` for the authoritative shape. Per adjustments2.md §6, we avoid labelling the hash input as "canonical key":

| Entity type     | Hash input (fed to `sha256_text`)                     | ID                         |
|-----------------|-------------------------------------------------------|----------------------------|
| `ag:section`    | `source_hash + "::section::" + heading_slug_path + "::" + order_within_doc` | `ent_<sha256_text(id_input)>` |
| `ag:technology` | `source_hash + "::technology::" + normalized_token`   | `ent_<sha256_text(id_input)>` |
| `ag:reference`  | `source_hash + "::reference::" + target + "::" + order_within_doc`  | `ent_<sha256_text(id_input)>` |

where:

- `heading_slug_path` is the slash-joined slugified titles of every ancestor heading (`H1 > H2 > H3` → `h1-title/h2-title/h3-title`). Slugification: lowercase, spaces→hyphens, non-word chars stripped. Matches the existing project `canonical_key` helper.
- `order_within_doc` is the 0-based token-stream index of the heading/link.
- `normalized_token` is `token.casefold().strip()`.
- `target` is the raw `href` attribute from the token (pre-resolution), so that a link to `./foo.md` and a link to `foo.md` produce distinct reference entities (they point at different targets). Resolution to internal/external/unresolved happens in the entity body, not in the ID.

Link records produced (superseded by the simpler topology documented in `data-model.md §2` after the post-review adjustments pass; kept here for historical traceability):

| Link type               | From                | To                     | Rule ID                     | Emitted when                              |
|-------------------------|---------------------|------------------------|-----------------------------|-------------------------------------------|
| `contains_section`      | document or section | section (child)        | `link.markdown.contains_section.v1`     | every section                             |
| `mentions_technology`   | section             | technology             | `link.markdown.mentions_technology.v1`  | each section that contains the token     |
| `references`            | section             | `ag:reference`         | `link.markdown.references.v1`           | every reference (internal/external/unresolved) |
| `resolves_to_document`  | `ag:reference`      | `doc_<id>`             | `link.markdown.resolves_to_document.v1` | internal references only                 |

Unresolved and external references still emit the `references` edge from the section, so the graph is traversable from any section to any of its outbound references. Only the `resolves_to_document` edge is conditional on resolution.

**Rationale.**
- Source hash is already in every ref today; using it as the ID root means an edit anywhere in the file rotates all new-doc IDs (consistent with the cache-invalidation semantics of the ingest stage).
- Order-within-doc resolves ambiguity for repeated headings like "Examples" appearing in multiple sections.
- Heading slug path makes section IDs introspectable by humans (`canonical_key` is already used for notes).
- Full-SHA IDs match the existing `ent_<sha256>` convention and the sharding helper `shard_dir` (which takes the 2 chars after `ent_`).

**Alternatives considered.**
- Truncated 24-char SHA as the report proposed: rejected to keep consistency with existing entity sharding and URL-friendliness of IDs.
- Slug-only IDs: rejected because two files with the same heading titles would collide across documents.
- Hash over the body text: rejected — tiny edits inside a section body would rotate the section's ID, breaking stable graph navigation.

---

## R4. Migration behavior on existing workspaces

**Question.** What cache invalidation is needed to satisfy FR-016a ("next pipeline run re-runs extract against the full corpus, automatically")?

**Investigation.**

- Inspection of `run_extract` (`runner.py:554-670`) shows it **already re-runs entity production on every invocation**: it iterates all ingest records, rebuilds entities from scratch, writes via `write_entities(pkg_root, entity_list)`. There is no extract-stage cache to invalidate.
- The only cache in the pipeline is in `run_ingest` (`runner.py:162-175`): if a document with matching `source_hash` is on disk, the file is not re-parsed.
- Conclusion: once R2's fix lands, the extract stage naturally re-processes every record on the next run; new sub-entity producers activate and emit `ag:section` / `ag:technology` / `ag:reference` entities for the entire corpus without user intervention.

**Decision.** No separate invalidation mechanism. FR-016a and FR-016b are satisfied by the combination of (R2's backward-compat reader) + (existing unconditional re-extraction). Document this explicitly in `research.md` and `quickstart.md` so future changes don't re-introduce extract-stage caching without audit.

**Rationale.** The simplest possible mechanism is the one that's already in the code. Adding a producer-set fingerprint would be speculative (YAGNI per Constitution V).

**Alternatives considered.**
- Write a `producer_set_hash` into `extract-manifest.json`, compare on load, force re-extract on mismatch: rejected — solves a problem that doesn't exist. If a future change makes extract cache-aware, the producer-set fingerprint becomes necessary; call that out in the Refactoring audit of that future change.

---

## R5. Throughput-warning mechanism

**Question.** How should stages surface "zero-output given nonzero-input" without changing exit codes or breaking `outputs_hash` determinism?

**Investigation.**

- `StageManifest` (`auditgraph/storage/manifests.py`) is a frozen dataclass serialized to `runs/<run_id>/<stage>-manifest.json`. Existing fields: `version`, `schema_version`, `stage`, `run_id`, `started_at`, `finished_at`, `inputs_hash`, `outputs_hash`, `config_hash`, `status`, `artifacts`. Spec 027 added `redaction_postcondition` block to `index-manifest.json` via merge-at-write without a schema bump — precedent for additive fields.
- `StageResult` (`pipeline/runner.py:46-49`) has `stage`, `status`, `detail` and is emitted through CLI `_emit()`.
- Clarification Q5 pinned the threshold: exactly zero output given ≥1 input from prior stage.

**Decision.**

1. Add field `warnings: list[dict[str, str]]` to `StageManifest` (default `[]`). Each entry: `{"code": str, "message": str, "hint": str}`. Never participates in `outputs_hash`.
2. New module `auditgraph/pipeline/warnings.py` exports:

   ```python
   THROUGHPUT_WARNING_NO_ENTITIES = "no_entities_produced"
   THROUGHPUT_WARNING_EMPTY_INDEX = "empty_index"

   def throughput_warning(code: str, stage: str, upstream: int, produced: int) -> dict:
       """Return a structured warning for CLI + manifest."""
   ```

3. `run_extract` adds the warning when `produced_entities == 0 and upstream_ok_records >= 1`. `run_index` adds the warning when `bm25_entries == 0 and entities_on_disk >= 1`.
4. CLI `_emit(payload)` surfaces `warnings[]` whenever the StageResult carries them. Exit code unchanged.

**Rationale.**
- Additive field, no schema bump.
- Structured dicts with stable codes → greppable in manifests, machine-readable for CI assertions.
- Threshold is binary (per Q5), so no tuning, no false positives, no stage-specific config.
- Warnings live on the manifest so "inspect later" (FR-018) works from disk alone.

**Alternatives considered.**
- Emit to stderr only: loses the persistence requirement of FR-018.
- Use `StageManifest.status = "warn"`: would mean three status values, and every existing consumer that branches on `status == "ok"` would need updating. Rejected — too invasive for the benefit.
- Ratio-based threshold with config: explicitly deferred by Q5.

---

## R6. Node-lookup ID-prefix dispatch

**Question.** How does `node_view` resolve an entity ID to its on-disk record when different classes live under different subtrees?

**Investigation.**

- Current implementation (`auditgraph/query/node_view.py`): searches `chunks/` via `rglob`, then falls through to `load_entity(pkg_root, entity_id)` which scans `entities/<shard>/` — but **never** touches `documents/`.
- `load_entity` uses the `ent_<sha256>` shard convention: first 2 chars after `ent_` are the shard dir. Documents use `doc_<sha256>` and live under `documents/<doc_id>.json` (no shard dir).
- IDs encountered today: `ent_*` (notes, NER entities, sub-entities), `chk_*` (chunks), `doc_*` (documents), `commit_*` / `tag_*` / `ref_*` / `author_*` / `file_*` / `repo_*` (git provenance entities — which DO live under `entities/<shard>/` per Spec 020).
- Report's proposed fix: "ID-prefix dispatch … or promote documents to full entity status." Clarification Q accepted Option A equivalent (contract: resolves by ID regardless of subtree).

**Decision.** Rewrite `node_view` as a table-driven dispatcher:

```python
RESOLVERS = [
    ("doc_",   lambda pkg_root, id_: (pkg_root / "documents" / f"{id_}.json", DOC_VIEW)),
    ("chk_",   lambda pkg_root, id_: (_find_chunk(pkg_root, id_), CHUNK_VIEW)),
    # every other prefix (ent_, commit_, tag_, ref_, author_, file_, repo_, note_, ...)
    # → entities/<shard>/<id>.json
]
```

Behavior:
1. Try the prefix's preferred location first.
2. If not found there, fall through in prefix declaration order (belt-and-suspenders for legacy IDs that might live elsewhere).
3. If nothing resolves, return a single structured `{"status": "error", "code": "not_found", "message": "..."}` — not the path-specific OS error shown in the Orpheus repro.

**Rationale.**
- Table-driven dispatch beats per-type `if`/`elif` ladders (DRY).
- Fall-through preserves behavior for any legacy ID that happens to live in a non-prefix-matching location.
- Documents are not promoted to full entity status in this spec — that's a larger change that would need its own spec and would overlap with Spec-028's already-bundled scope.

**Alternatives considered.**
- Promote documents to full entity status: rejected — adds a schema migration and changes adjacency semantics (documents would participate in link graph in a way they don't today). Too big for a polish fix.
- Scan every subtree regardless of prefix: rejected — wasteful on large workspaces and conflicts with the readability argument for structured storage.

---

## R7. Wall-clock timestamps without breaking determinism

**Question.** How do we record real invocation time in manifests while preserving `outputs_hash` stability across runs?

**Investigation.**

- `started_at` / `finished_at` today are filled by `self._deterministic_time_for(run_id)` (`runner.py:121,122,269,270,1029,1030`), which wraps `auditgraph.storage.hashing.deterministic_timestamp(seed)`:

  ```python
  digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
  seconds = int(digest[:8], 16) % (10**9)
  dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
  ```

  Hashes the run_id into a seconds value in a 31-year window starting from 1970. The `1995-12-23T04:33:39Z` timestamps the Orpheus report called "clearly a fixed deterministic placeholder" are **real** stable artifacts of this function, not a test fixture leaking. The report misdiagnosed the cause — but the user-facing symptom (fake timestamps in production manifests) and fix are the same.
- `outputs_hash` is computed separately from a sorted JSON of stage-specific content (e.g., `extract` uses entity IDs + claim IDs + ner_link paths; `runner.py:632-638`). It does **not** include `started_at` / `finished_at`. Determinism is already decoupled from timestamps today; the deterministic timestamps are there only to make the full manifest byte-identical across runs.
- Implication: we can safely add *new* wall-clock fields without risking existing hash-stability tests. But if we *change* `started_at` / `finished_at` to wall-clock, some manifest-byte-identity tests may break.

**Decision.** Add two new fields to `StageManifest` and `IngestManifest`:

- `wall_clock_started_at: str | None` — ISO-8601 UTC timestamp of actual invocation.
- `wall_clock_finished_at: str | None` — same, at stage completion.

Keep `started_at` / `finished_at` as the existing deterministic values (they may still appear in some downstream consumers; no risk of break). Expose a `wall_clock_now()` helper in `storage/hashing.py` (the utility shim for the new fields — not a "hash" but colocated since it's the time producer). Unit-test suite pins the helper via monkeypatch to keep hash-stability tests deterministic; production code path reads real time.

**Rationale.**
- Addresses FR-027 (real timestamps visible to operators) without risking FR-028 (deterministic reproducibility).
- Matches exactly the report's BUG-3 proposed fix: "Keep wall-clock timestamps in `wall_clock_started_at` / `wall_clock_finished_at`; keep the deterministic placeholder only for the fields that feed `outputs_hash`."
- Splits responsibilities — the new fields have no hashing semantics, so any future change to `outputs_hash` can't accidentally pull them in.

**Alternatives considered.**
- Replace `started_at`/`finished_at` with wall-clock: rejected — breaks any test that asserts byte-identity across runs of stage manifests. Existing determinism tests are load-bearing.
- Use a single composite `timestamps` dict: more nesting for no gain; rejected for ergonomics.

---

## R8. Rule-pack validator shape and failure modes

**Question.** How does the config loader validate that `extraction.rule_packs` and `linking.rule_packs` point at files that exist and are readable, without regressing for users who have customized their config?

**Investigation.**

- `config/pkg.yaml:57-58,109-110` declares `rule_packs: ["config/extractors/core.yaml"]` and `rule_packs: ["config/link_rules/core.yaml"]`. Both directories are empty in the shipped repo.
- `auditgraph/config.py:59-60` defaults mirror the same paths.
- No current loader reads these paths. The shipped code silently ignores them; rule-pack loading is a TODO placeholder.
- The simplest user-observable contract per Q4 (US4 in spec): "no silent misconfiguration." Missing path → error. Malformed path → distinct error. Happy path → no-op.

**Decision.**

1. Ship `config/extractors/core.yaml` and `config/link_rules/core.yaml` as minimal but schema-valid stubs:

   ```yaml
   version: v1
   extractors: []  # populated in future specs; empty = no custom rules
   ```

   (and mirror for `link_rules`). These satisfy FR-021 out of the box.

2. New module `auditgraph/utils/rule_packs.py`:

   ```python
   @dataclass
   class RulePackError(Exception):
       kind: str  # "missing" | "malformed"
       path: str
       reason: str

   def validate_rule_pack_paths(
       paths: Iterable[str],
       workspace_root: Path,
   ) -> None:
       """Raise RulePackError on any missing or malformed path.

       Relative paths in `paths` are resolved against `workspace_root`
       (the directory containing `config/pkg.yaml`) — NOT against the
       config file's parent. The latter causes `config/config/...` path
       doubling; see contracts/rule-pack-validator.md for the authoritative
       resolution rule.
       """
   ```

3. `auditgraph/config.py`'s config loader (at the point the profile dict is materialized) iterates `extraction.rule_packs` and `linking.rule_packs`, passes each list through the validator. Failures surface as structured CLI errors with non-zero exit codes (following the Spec-027 pattern for `Neo4jTlsRequiredError`).

4. Malformed YAML triggers a `kind="malformed"` error — distinct from `kind="missing"` — per FR-023.

**Rationale.**
- Two-part fix satisfies both the "ship defaults" and "fail-loud" arms of the Orpheus report's BUG-2 proposal. The user's observable contract ("no silent misconfiguration") is met regardless of whether they kept defaults or customized them.
- One new validator module per Single Responsibility (Constitution II).
- Reuses PyYAML (already a declared dep) for parsing.

**Alternatives considered.**
- Ship defaults only, skip validation: cheap but fragile — any future config drift re-opens the silent-failure door.
- Validate only, ship no defaults: brittle for `auditgraph init` UX — new users would hit a validation error immediately on first run.
- Promote rule packs to full schema-validated structured docs via jsonschema (already a dep from Spec 027): overkill for this spec. YAML-syntax validation is enough; contents-schema validation is a future spec when rules are actually populated.

---

## R9. Source of redacted markdown text for the extractor (post-review)

**Question.** The extractor takes `markdown_text` but the current pipeline doesn't persist full redacted markdown text in any obvious location. Where does the runner get it?

**Investigation.**

- Ingest parses the source with `parse_file` → `_build_document_metadata` (`auditgraph/ingest/parsers.py:47-141`). The redacted `text` variable exists transiently during metadata construction but is not stored — only the segmented and chunked decompositions are written to disk.
- Chunks and segments overlap and drop structural markers (heading fences are absorbed into segment text, but the decomposition isn't reversible into the original markdown syntax the token walker needs).
- Options: (a) persist redacted full text on the document record; (b) re-read the source file in extract and re-redact; (c) reconstruct from chunks.

**Decision.** Option (a): add a `text` field to the `document` payload (written into `documents/<doc_id>.json`). Populated only when `parser_id == "text/markdown"` so non-markdown document payloads stay byte-identical. The extract stage reads this field to feed the markdown sub-entity extractor.

**Rationale.**
- Preserves the canonical-redaction-site principle from Spec 027 (FR-016): parser entry is the only site that applies redaction. Re-reading + re-redacting in extract would introduce a second site and violate the principle.
- O(1) cost at ingest (we already have the redacted text in memory); no re-I/O at extract.
- Additive field on an existing record → no schema version bump.
- Bloat is limited: markdown corpora are typically small (≤ 1 MB per file); persisting the full text once per document doubles neither the chunk storage nor the adjacency index.

**Alternatives considered.**
- Re-read the source in extract: rejected for the Spec-027 redaction-site violation.
- Reconstruct from chunks: rejected for lossiness (chunk overlap, markdown syntax consumed by the chunker).
- Separate sidecar `documents/<doc_id>.text`: rejected for the extra file-per-document cost with no architectural benefit over a field on the JSON.

---

## R10. Token-emission rules for `ag:technology` and `ag:reference` (post-review)

**Question.** What specifically does a fenced code block emit? What about images, bare URLs, reference-style links?

**Investigation.**

- A markdown-it `fence` token has an `info` string (the language tag) and a `content` string (the block body). `code_inline` tokens carry just `content`.
- If we tokenize fenced block BODY content into technology entities, a 50-line bash script produces 50–500 technology entities — matching adjustment #6's noise concern.
- markdown-it-py's `linkify` option (disabled by default) is what turns bare URLs in text into `link_open/link_close` tokens. Without it, `https://example.com` stays a plain text run.

**Decision.**

- Inline code span → one `ag:technology` per span.
- Fenced block → exactly one `ag:technology` whose token = `info` string; empty info → no entity; body content NOT mined.
- Indented code block → no `ag:technology` (no info string).
- Images (`![alt](src)`) → no entity of either type in v1. Image references can be added in a follow-on spec if user demand emerges.
- Bare URLs → captured via `MarkdownIt("commonmark", {"linkify": True}).enable("linkify")` — BOTH the option and the rule are required (belt-and-suspenders; see `contracts/markdown-subentities.md` parser-configuration section for the authoritative form). Autolinks (`<url>`) captured unconditionally.
- Reference-style links → markdown-it-py resolves labels during `.parse()` into the same `link_open/link_close` token sequence as inline links. No additional handling needed.

**Rationale.**
- "One technology per fence" turns code blocks into stack-signal edges (`bash`, `python`, `yaml`) instead of word-level noise.
- Ignoring indented code blocks follows the same "no info string, no signal" rule.
- Enabling `linkify` makes prose URLs queryable without requiring authors to wrap them in `<>` — matches how users actually write markdown.
- Skipping images in v1 keeps the spec bounded; images carry alt text and captions that would benefit from different semantics than links.

**Alternatives considered.**
- Emit one entity per line of fenced block: noisy, no dedup story, low signal.
- Emit one entity per shell-like word in fenced block: requires language-aware tokenization (a rabbit hole).
- Default `linkify` off: would skip a common style of markdown URL citation.

---

## R11. Stale-entity handling under source-hash-rooted IDs (post-review)

**Question.** With every markdown sub-entity ID derived from `source_hash`, editing any file rotates the IDs and leaves pre-edit entities as disk-resident orphans. Prune, or accept staleness?

**Investigation.**

- Inspection of `write_entities` / `write_links` in `auditgraph/extract/manifest.py` and `auditgraph/link/links.py` confirms both are additive: they write new entity/link files but never delete existing ones that don't appear in the new input set.
- The existing `note` entity uses `canonical_key(title)` as its ID input — title-stable, so notes don't rotate when the body changes. The new sub-entity types, in contrast, rotate on every content edit.
- Without pruning, a user who renames a heading from "Install" to "Installation" ends up with both sections in the store forever.

**Decision.** Active pruning scoped to the three markdown sub-entity types (and their originating link rule IDs). For each source being (re-)extracted in this run, before writing the refreshed entities, the runner enumerates on-disk `ag:section` / `ag:technology` / `ag:reference` entities whose `refs[0].source_path` matches the current source and deletes them. Same for `link.markdown.*.v1` link records whose from-side entity points at that source.

**Rationale.**
- Users expect the entity store to reflect current source state (quickstart-level expectation).
- Type-scoped pruning guarantees we never touch `note`, NER, git-provenance, or user-introduced records — the blast radius is bounded and auditable.
- Alternatives (e.g., a cross-cutting garbage collection pass) are larger-scope and orthogonal; if spec-029+ introduces cross-source orphan cleanup, this pruning hook can be reused or subsumed.

**Alternatives considered.**
- Accept staleness + document: rejected; hides bugs and degrades queries over time.
- Prune everything whose source_hash isn't referenced by the current ingest manifest: broader but risks touching non-markdown entities from other pipelines. Rejected for blast-radius.
- Root IDs in `canonical_key` only (no source_hash): contradicts R3 (source_hash is what makes two docs with the same heading title produce distinct sections). Rejected.

---

## R12. Cooccurrence exclusion for new entity types (post-review)

**Question.** `build_source_cooccurrence_links` (at `auditgraph/link/rules.py`) produces `relates_to` links between every pair of entities sharing a source. If markdown sub-entities participate, a document with 30 sub-entities produces ~435 cooccurrence pairs — pure noise.

**Investigation.**

- `build_source_cooccurrence_links` iterates entities grouped by `source_path` and emits pairs. No type filter exists today — it treats every entity equivalently.
- Spec-028 multiplies sub-entity counts by ~10–30 per markdown file. The existing NER path is similarly productive on news-style text but is off by default.
- The explicit markdown link types (`contains_section`, `mentions_technology`, `references`, `resolves_to_document`) already carry all the meaningful markdown relationships at precision 1.0.

**Decision.** Exclude `ag:section`, `ag:technology`, `ag:reference` from `build_source_cooccurrence_links`. Implementation: add a type-filter list (defaulting to include the new types) and drop any entity whose `type` is in the exclusion set before emitting pairs. Preserves cooccurrence behavior for all existing types.

**Rationale.**
- Matches the "explicit links are the canonical graph" principle.
- Keeps `relates_to` meaningful for notes, git-provenance, and future entity types that don't have dedicated link rules.
- Cheap to implement: one set membership check per entity in a loop that already iterates entities.

**Alternatives considered.**
- Emit cooccurrence links but mark them with lower confidence: rejected; downstream queries don't filter by confidence by default, so they'd still be noisy.
- Let users opt out via config: rejected; defaulting to noise and requiring a switch to make the tool useful is the wrong direction.

---

## Research summary

| Thread | Decision | Unknown resolved |
|--------|----------|------------------|
| R1     | `markdown-it-py>=4,<5` (matches uv.lock 4.0.0) | Primary Dependencies |
| R2     | Orthogonal `source_origin` field + backward-compat reader | BUG-1 fix path |
| R3     | Source-scoped hash input for ALL three new types; `canonical_key` is a separate human-readable field | Sub-entity ID determinism |
| R4     | No new cache invalidation; existing re-extract covers migration | FR-016a mechanism |
| R5     | `StageManifest.warnings` + binary zero-threshold | Throughput warning shape |
| R6     | Table-driven prefix dispatch in `node_view` with fall-through | BUG-4 fix path |
| R7     | New `wall_clock_*` fields; preserve deterministic `started_at` | BUG-3 without regressing determinism |
| R8     | Ship stubs as package data + init copies them + validator falls back to package resources | BUG-2 fix path (complete) |
| R9     | Persist redacted full markdown text on the `document` record; extract reads it | Markdown text source for extractor |
| R10    | Fence-info-only technology emission; linkify-enabled; images skipped in v1 | Token rules for ag:technology and ag:reference |
| R11    | Active type-scoped pruning before each re-extract | Stale-entity handling |
| R12    | Exclude new types from source cooccurrence | Scaling protection for relates_to graph |

Every NEEDS CLARIFICATION from `plan.md`'s Technical Context is resolved. Phase 1 (data model, contracts, quickstart) can proceed.
