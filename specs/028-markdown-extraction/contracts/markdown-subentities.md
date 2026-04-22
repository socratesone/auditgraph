# Contract: `extract_markdown_subentities`

**Module**: `auditgraph/extract/markdown.py`
**Consumer**: `auditgraph/pipeline/runner.py :: run_extract`

## Public signature

```python
@dataclass(frozen=True)
class DocumentsIndex:
    """Bi-directional lookup for reference classification.

    The forward map is used when formatting resolved internal references
    (to emit the target's document_id on the entity and on the
    resolves_to_document link). The reverse map is used at classification
    time to decide whether a target path was actually ingested AS PART OF
    THE CURRENT RUN.

    Construction rule (per adjustments3.md §4): the index MUST be built
    from the current ingest manifest's records where ``parse_status == "ok"``
    (after normalization per R2), not from a disk scan of ``documents/``.
    Stale document files from prior runs whose sources have since been
    deleted or excluded MUST NOT appear in this index — otherwise links
    to those paths would falsely classify as ``internal`` and produce
    dangling ``resolves_to_document`` edges.
    """
    by_doc_id: Mapping[str, Path]              # doc_id -> on-disk documents/<doc_id>.json
    by_source_path: Mapping[str, str]          # normalized workspace-relative source_path -> doc_id

def extract_markdown_subentities(
    *,
    source_path: str,
    source_hash: str,
    document_id: str,
    document_anchor_id: str,
    markdown_text: str,
    redactor: Redactor,
    documents_index: DocumentsIndex,
    pipeline_version: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """
    Walk a markdown source and emit (entities, links).

    Parameters
    ----------
    source_path
        POSIX path of the source file, workspace-relative.
    source_hash
        SHA-256 of the source file's raw bytes.
    document_id
        Document ID produced at ingest time. The runner passes the authoritative
        value from the persisted `documents/<doc_id>.json :: document_id` field;
        the extractor MUST NOT recompute it from path + hash (the runner is the
        single source of truth for document identity, per adjustments3.md §5).
    document_anchor_id
        The note entity ID that the runner just produced via ``build_note_entity``
        for this source. Top-level ``contains_section`` links (and the topology
        for pre-heading references/technologies per §Pre-heading content below)
        attach to this anchor. Passing it explicitly keeps the extractor from
        having to recompute the note ID (which depends on title/frontmatter logic
        that lives in ``build_note_entity`` and could drift).
    markdown_text
        The **already-redacted** full markdown text. The runner obtains
        this from ``documents/<doc_id>.json :: document.text`` (persisted
        by ingest per FR-015a). This function is the second redaction
        check (belt and suspenders), not the canonical site — Spec 027
        FR-016 is authoritative.
    redactor
        Spec-027 canonical redactor. Applied to every string field emitted.
    documents_index
        Bi-directional lookup populated by the runner from the set of
        ``documents/`` records materialized in the current run.
    pipeline_version
        Propagated into every entity's ``provenance.pipeline_version``.

    Returns
    -------
    (entities, links)
        Two lists of dicts conforming to the shapes in data-model.md.
        ``entities`` contains only ag:section / ag:technology / ag:reference
        records; it does NOT contain the note-level entity (that stays
        with build_note_entity).
    """
```

## Preconditions

1. `markdown_text` has already passed through `redactor.redact_text(...)` in the ingest stage (Spec 027 FR-016) and has been persisted on the document record. The runner reads it from `documents/<doc_id>.json :: document.text` before invoking this function. No source-file re-reading happens in the extract stage.
2. The caller guarantees that `source_hash` corresponds to the original source bytes at the time `markdown_text` was produced. The extractor does NOT verify this — it is pure w.r.t. I/O and cannot compute `sha256_file(source_path)` itself. Any mismatch is an integration bug (e.g., the runner passed mismatched arguments), not the extractor's responsibility to detect.
3. `document_id` is passed in by the caller from the authoritative on-disk source — `documents/<doc_id>.json :: document_id` — read by the runner BEFORE invoking this function. The extractor MUST NOT recompute `document_id` from `(source_path, source_hash)` because ingest is the canonical producer of the ID and any change to ingest's path-normalization rules would otherwise silently diverge from the extractor. Note: today's ingest uses `deterministic_document_id(path.as_posix(), source_hash)` — the extractor trusts this instead of duplicating the computation.
4. `documents_index` reflects the state of `documents/` **at the time of this call** — stale snapshots are an integration bug, not handled here.
5. `documents_index.by_source_path` keys are normalized workspace-relative POSIX paths. Relative targets in markdown are normalized the same way (join against `Path(source_path).parent`, then `.resolve()` against the workspace root, then `.as_posix()` relative to the root) before lookup.

## Postconditions

1. Returned `entities` list:
   - Contains zero or more dicts, each with `type` in `{"ag:section", "ag:technology", "ag:reference"}`.
   - No two entities share an `id` (pre-dedup at the emit site).
   - Every entity has all the required fields from `data-model.md §1`.
   - Every text field has been passed through `redactor`.
2. Returned `links` list:
   - Contains zero or more dicts conforming to `data-model.md §2`.
   - Every link references an entity whose `id` appears in the returned entities list **or** in `documents_index.by_doc_id` keys (for `resolves_to_document` edges, whose `to_id` is a `doc_…` rather than an entity record).
   - No link references an entity that does not exist in the run.
3. Determinism: calling this function twice with identical arguments MUST produce byte-identical returns (dict key ordering, list ordering, field values).
4. No I/O: this function MUST NOT touch the filesystem, the network, or any external process. It is pure with respect to its arguments.

## Errors

- `ValueError` if any precondition is violated.
- `markdown_it.MarkdownItError` (bubbled unchanged) if the parser fails. Upstream `run_extract` translates this into a record-level skip without killing the whole stage.

## Token-rule specification (authoritative for ag:technology and ag:reference emission)

### `ag:technology`

- **Inline code span** (`` `token` ``): emit one `ag:technology` entity per span; `token` = span content; `origin = "code_inline"`.
- **Fenced code block** (``` ```lang \n body \n``` ```): emit exactly one `ag:technology` entity where `token = info_string` (the language tag) and `origin = "fence"`. Empty `info` → no entity. Block body content is NOT scanned for tokens.
- **Indented code block** (four-space prefix): emit no entity (no info string exists for indented blocks).
- Per-document dedup key is `normalized_token = token.casefold().strip()`.

### Pre-heading content

Markdown content that appears BEFORE the first heading (or in a file with no headings at all) has no enclosing `ag:section`. Such references and technologies MUST attach to the document anchor (`document_anchor_id` = the note entity for this source) instead. Concretely:

- A `code_inline` or `fence` token encountered before any `heading_open` token produces an `ag:technology` whose `mentions_technology` edge (if any) originates at `document_anchor_id`, not at a section.
- A `link_open` / link token encountered before any `heading_open` token produces an `ag:reference` whose `references` edge originates at `document_anchor_id`, not at a section.
- A markdown file with zero headings still emits `ag:technology` and `ag:reference` entities for any code or links it contains; all such edges originate at `document_anchor_id`.

This rule keeps the graph topology uniform: every sub-entity has a deterministic origin edge, whether an enclosing section exists or not. Tests for this behavior are listed in the Test contract below.

### `ag:reference`

- **Inline link** `[text](href "title")`: emit one `ag:reference` with `target = href`.
- **Autolink** `<https://example.com>`: emit one `ag:reference` with `target = href`.
- **Bare URL** `https://example.com` (no wrapping): emit one `ag:reference` — this requires the parser adapter to enable markdown-it-py's `linkify` option.
- **Reference-style link** `[text][label]` + `[label]: url`: the parser resolves the label internally; emit one `ag:reference` with `target = url`.
- **Image** `![alt](src)`: emit NO `ag:reference` and NO `ag:technology` in v1.

### Parser configuration (authoritative, fixes adjustments3.md §1)

The adapter function `_tokenize(text: str) -> Iterable[Token]` MUST instantiate the parser with BOTH the `linkify` option set in the constructor AND the `linkify` rule enabled. Belt-and-suspenders — the option alone is insufficient on some markdown-it-py versions, and `.enable("linkify")` alone silently no-ops when the rule is absent from the preset's default rule set. The authoritative form is:

```python
from markdown_it import MarkdownIt

def _tokenize(text: str) -> list:
    md = MarkdownIt("commonmark", {"linkify": True}).enable("linkify")
    return md.parse(text)
```

This is the ONLY parser setup that appears in any normative artifact. Any other form (bare `MarkdownIt()`, option-only, rule-only) is a spec violation.

### Parser configuration dependency

`linkify-it-py` MUST be installed at runtime for the above configuration to detect bare URLs. It is pulled in by the `markdown-it-py[linkify]` extras declaration in `pyproject.toml` (per FR-016h and T001). Without it, `.enable("linkify")` is a silent no-op and bare URLs in prose stay as text runs. The regression test for this (T019a) fails if `linkify-it-py` is absent.

## Test contract

Minimum test coverage (in `tests/test_spec028_markdown_*.py`):

- **Determinism**: call twice with identical inputs, assert byte-identical outputs.
- **Empty input**: empty `markdown_text` → empty entities, empty links.
- **Frontmatter-only**: YAML frontmatter with no body → empty entities, empty links.
- **Single H1**: one section entity, no parent link.
- **Nested headings (H1 → H2 → H3)**: three section entities; `parent_section_id` chain intact.
- **Code dedup**: `PostgreSQL` and `postgresql` in the same doc → one `ag:technology` entity.
- **Code across documents**: same token in two docs → two entities (no cross-doc dedup).
- **Fenced block emits info string only**: ``` ```bash\nrm -rf /\n``` ``` → one `ag:technology` with token `"bash"`, nothing for `rm`, `-rf`, `/`.
- **Fenced block with empty info**: ``` ```\nsome code\n``` ``` → no `ag:technology` entity.
- **Indented code block**: four-space-indented content → no `ag:technology` entity.
- **Link classification (expanded)**: `[foo](./doc.md)` internal, `https://example.com` external, `<https://example.com>` external, bare `https://example.com` in prose external (via linkify), `./missing.md` unresolved, `#anchor` unresolved, `setup.md#install` classified on the path, `./setup/` (directory/bare) unresolved, `./doc.md?q=1` classified on the path.
- **Graph topology**: every `ag:reference` has exactly one inbound `references` link; only internal references have an outbound `resolves_to_document` link.
- **Image skip**: `![diagram](arch.png)` produces no entity.
- **Redaction defense-in-depth**: pass a mock `Redactor` that counts calls; assert every emitted string field triggered at least one call.
- **Order stability**: fixture with multiple same-text headings; assert the section IDs differ by `order`.

## Non-goals

- Does not produce the note-level entity (that remains `build_note_entity` per the runner's existing structure).
- Does not write to disk (that's `run_extract`'s job via `write_entities` / `write_links`).
- Does not resolve link targets across runs — `documents_index` is authoritative for this invocation only.
- Does not re-read the source file from disk — it receives `markdown_text` from the caller (runner) which got it from the `document.text` field.
- Does not perform pruning — pruning of stale entities is the runner's responsibility, invoked BEFORE this extractor runs per FR-016c.
