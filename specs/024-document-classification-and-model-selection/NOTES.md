# 024 — Document Classification & Dynamic Model Selection (Pre-spec Notes)

**Status**: Pre-spec notes — NOT ready for `/speckit.specify`. Capture phase only.
**Created**: 2026-04-07
**Author of these notes**: Joshua Albert (via session with Claude)
**Trigger**: Issue 3 NER quality discussion during the post-Spec-023 session.

This file is a stash for thoughts on a future spec. It is not a spec yet.
When this work is ready to begin, run `/speckit.specify` against the
distilled requirements below and let it bloom into a real spec.

---

## The core observation

Right now, auditgraph treats every ingestable document the same way:
- One ingest pipeline (`auditgraph/ingest/parsers.py`) routes by file
  extension into a small number of parser_ids (`text/markdown`,
  `text/plain`, `text/code`, `document/pdf`, `document/docx`).
- One chunker (`auditgraph/utils/chunking.py`) is applied uniformly to
  whichever parser branches call `_build_document_metadata`.
- One NER pipeline (`auditgraph/extract/ner.py`) loads exactly one
  spaCy model from config and runs it against every chunk.
- One markdown noise stripper (when added in Issue 3 Phase 2) will
  apply only to markdown source paths.

This works for trivial cases but breaks down once the workspace contains
heterogeneous content. A research paper, a legal contract, a transcript,
a markdown note, and a PDF scan of a historical document all have
different ideal handling — but auditgraph applies the same logic to all
of them.

## Concrete problems this would solve

### 1. NER model is wrong for technical content (Issue 3, partial fix)

`en_core_web_sm` is trained on news/web text. On a research paper it
produces ~95% false positives because it doesn't recognize ML
terminology. SciSpaCy's `en_core_sci_sm` would be much better for
scientific content. Legal-domain models exist for contracts. There is
no "best" general model — the right model depends on what's being
ingested.

The current config supports a single global `model` field. Changing it
requires editing config and re-running ingest. There is no per-document
model selection.

### 2. PDF/DOCX noise leakage is unverified (Issue 3, partial — needs investigation)

Issue 3 Phase 2 adds a markdown-noise stripper for `text/markdown`
chunks (citation tokens, heading markers, code fences, etc.). But:

- **Do PDFs have analogous noise?** Page headers, footers, page
  numbers, OCR artifacts, broken hyphenation across line breaks, table
  formatting tokens, footnote markers (`[1]`, `*`)?
- **Do DOCXs have analogous noise?** Style markers, embedded XML,
  comment markers, track-changes residue?
- **Does plain text have analogous noise?** Headers/footers from email
  exports, signature blocks, threading markers (`>`, `>>`)?

Issue 3 Phase 2 only addresses markdown. We need to verify each parser's
output to see what slips through. Specifically:

- `auditgraph/extract/pdf_backend.py` — what does the extracted text
  actually look like? Is layout preserved, stripped, or somewhere in
  between?
- `auditgraph/extract/docx_backend.py` — same question.
- `auditgraph/utils/chunking.py` — does chunking break across natural
  document boundaries (paragraphs, sections, pages)?

The test would be: ingest a representative document of each type and
inspect the resulting chunk JSON files. Look for non-content tokens
that would confuse downstream extraction (NER, BM25, future LLM
backends).

### 3. The chunker is one-size-fits-all

A 200-token sliding window with 40-token overlap is appropriate for
prose but wrong for:

- **Legal contracts**: clause boundaries matter; cutting mid-clause
  destroys meaning.
- **Source code**: function/class boundaries matter; token-based
  chunking is meaningless. This is its own substantial concern — see
  § 4 below for the full analysis of the code structure gap (the
  existing `extract.code_symbols.v1` doesn't actually extract symbols).
- **Tables / structured data**: row boundaries matter; chunking by
  token destroys row coherence.
- **Transcripts**: speaker turns matter; cutting mid-turn loses
  speaker attribution.
- **Markdown with frontmatter**: the frontmatter shouldn't be chunked
  at all; it's metadata.

A document classification system would route each document to a
chunker appropriate for its type.

### 4. Code structure understanding is shallow (Issue 2, partial)

The opt-in `ingestion.chunk_code.enabled` flag from the post-Spec-023
quality sweep gives users a token-based escape hatch for code BM25
search, but it doesn't address the deeper gap: auditgraph has no real
understanding of code structure.

**What `extract.code_symbols.v1` actually does today** (verified by
reading `auditgraph/extract/code_symbols.py`):

```python
def extract_code_symbols(root, paths):
    symbols = []
    for path in paths:
        if path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx"}:
            continue
        normalized = normalize_path(path, root=root)
        symbols.append({
            "type": "file",
            "name": path.name,
            "canonical_key": f"file:{normalized}",
            "source_path": normalized,
        })
    return symbols
```

That's the whole function. **The name is a lie.** It doesn't extract
symbols — it creates one `file` entity per file with just a name, a
canonical key, and the source path. There are no function entities, no
class entities, no method entities, no import relationships, no
call edges. A Python file with 50 functions is the same one node as
an empty `__init__.py`. The extractor was named for its intent, not
its implementation.

**Why this matters**:

- `auditgraph query --q "load_ner_model"` cannot find a function by
  name even when BM25 chunks are enabled, because the chunker is
  character-based and the function name is buried inside a chunk.
- `auditgraph neighbors <file_id>` returns nothing useful. A `file`
  entity has no outbound edges (the existing cooccurrence rule skips
  single-entity files and code files produce one entity per file).
- Co-occurrence linking produces zero links between code entities,
  because there's only ever one entity per source file, so no pair
  ever shares a source.
- `auditgraph list --type file` is a flat list of paths with no
  structure. Users expecting to navigate a codebase get nothing the
  filesystem doesn't already offer.
- Git provenance (Spec 020) can answer "who authored this file"
  but not "who authored this function" — and functions are usually
  the unit of interest, not files.

**What a real code structure extractor would look like**:

New entity types:
- `code:module` — one per file, replaces or extends the current `file`
- `code:function` — one per top-level function or method
- `code:class` — one per class definition
- `code:import` — one per import statement (or one per imported symbol)

New link types:
- `defined_in` — function/class → module
- `method_of` — method → class
- `imports` — module → imported symbol or module
- `calls` — function → function it calls (hardest; needs resolver)
- `inherits_from` — class → base class
- `decorates` — decorator → function/class it decorates

Per-language parser strategy:
- **Python**: stdlib `ast` module. Fast, no deps, built-in. Handles
  module/class/function/import extraction trivially. Call graphs
  require a resolver (libraries like `astroid` or `jedi` do this).
- **JavaScript/TypeScript**: no stdlib parser. Options are
  `tree-sitter-javascript`/`tree-sitter-typescript` (C extension,
  fast, consistent API across languages) or `esprima` (pure-Python,
  older, JS-only). Tree-sitter is the better long-term bet but adds
  a C dependency.
- **Multi-language**: tree-sitter covers most languages with a
  consistent API. Could be the foundation for a general code
  extractor. Ships as `tree_sitter` + per-grammar packages.

Per-symbol chunking:
- Each `code:function` entity's `text` field is the function body.
- Each `code:class` entity's `text` field is the class body including
  docstring.
- Each `code:module` entity's `text` field is the module docstring +
  top-level comments (the "file header" content).
- No sliding-window chunking. Chunk boundaries follow AST node
  boundaries. One chunk per symbol.

BM25 indexing implications:
- BM25 now indexes function bodies, class bodies, and docstrings —
  but as per-symbol chunks rather than per-file blobs. A search for
  "authenticate" finds every function whose body contains that
  string, with a direct pointer to the containing symbol.
- The entity's `name` field carries the symbol name (`load_ner_model`,
  `PipelineRunner`), so BM25 over entity names also works.
- Aliases could include short forms (`load_ner_model` → `load_ner`).

### 5. There's no document type beyond extension

The current `parser_id` is purely extension-based:
- `.pdf` → `document/pdf`
- `.md` → `text/markdown`
- ...

This doesn't capture meaningful subtypes:
- Is the markdown a research note, a meeting transcript, an ADR, a
  blog post, a Jupyter export?
- Is the PDF a scan, a born-digital paper, a contract, a slide deck?
- Is the plain text email, source code masquerading as `.txt`, a
  log file, an OCR dump?

Each subtype warrants different parsing, chunking, NER model, and
metadata extraction. The file extension is at best a weak hint.

## What a future spec might look like

### Core abstraction: DocumentClassifier

A function (or pluggable rule-set) that takes a parsed file and returns:

```
@dataclass
class DocumentClassification:
    primary_type: str          # "research_paper", "legal_contract",
                               # "personal_note", "transcript",
                               # "code_documentation", "scan_ocr", ...
    confidence: float
    detected_features: dict    # heuristics that produced the classification
```

Classification could be done by:
- Filename heuristics (keywords like "ADR", "transcript", "RFC", "spec")
- Frontmatter inspection (markdown frontmatter often declares type)
- First-N-token inspection (heuristic patterns: "Abstract\n", "1. INTRODUCTION", "Dear ", numeric clause headers)
- Path heuristics (`/notes/`, `/contracts/`, `/papers/`, `/transcripts/`)
- Optional: a small LLM call (deferred to v2 — local-first first)

### Per-classification processing pipelines

Each classification routes through a pipeline of (chunker, noise_stripper, NER_model, link_rules):

```yaml
profiles:
  default:
    document_classification:
      enabled: true
      classifiers:
        - rule: research_paper
          chunker: section_aware     # split on ## headings
          noise_stripper: markdown_with_citations
          ner_model: en_core_sci_sm
          link_rules: [scientific]
        - rule: personal_note
          chunker: paragraph
          noise_stripper: markdown_basic
          ner_model: en_core_web_sm
          link_rules: [generic]
        - rule: legal_contract
          chunker: clause_aware
          noise_stripper: legal_boilerplate
          ner_model: en_core_legal_sm  # would need to find/build this
          link_rules: [legal]
        - rule: default
          chunker: sliding_window_200
          noise_stripper: none
          ner_model: en_core_web_sm
          link_rules: [generic]
```

### Per-document model loading and caching

Multiple spaCy models loaded on-demand and cached at module level (the
existing `_cached_models` dict in `ner_backend.py` already supports this
pattern). Models that are never used are never loaded.

### Document-level metadata enrichment

Each document gets classification metadata stored in its document record
so queries can filter by type:

```bash
auditgraph list --type document --where "classification=research_paper"
```

This pairs naturally with the Spec 023 filter framework — no new query
infrastructure needed.

## Things to verify before writing the spec

1. **What does PDF extracted text actually look like?** Read a few
   chunks from a PDF ingest and check for noise patterns. Specifically:
   - Page headers/footers
   - Page numbers
   - OCR errors (if OCR is used)
   - Hyphenation breaks (`hyphen-\nation` → `hyphenation`?)
   - Footnote markers
   - Reference list formatting
   - Equation rendering

2. **What does DOCX extracted text look like?** Same as above for:
   - Style residue
   - Comment markers
   - Track-changes residue
   - Header/footer extraction
   - Table cell flattening

3. **What does the existing chunker do at boundaries?** Specifically:
   - Does it respect paragraph breaks?
   - Does it cut mid-sentence?
   - Does the 40-token overlap actually preserve context, or is it just
     duplicate boilerplate?

4. **What spaCy models exist for the domains we care about?**
   - SciSpaCy: `en_core_sci_sm`, `en_core_sci_md`, `en_ner_bionlp13cg_md`
     (biomedical entity types)
   - Legal: harder to find, may require fine-tuning
   - General large: `en_core_web_lg`, `en_core_web_trf`
   - Multilingual: `xx_ent_wiki_sm`

5. **What's the model loading overhead?** SciSpaCy models are larger
   than `en_core_web_sm`. Loading multiple models for a mixed-content
   ingest could be substantial. Need to measure.

6. **Should classification also affect entity types?** A research paper
   should probably emit `paper:author`, `paper:venue`, `paper:method`
   rather than generic `ner:person`. A legal contract should emit
   `legal:party`, `legal:date_of_execution`, `legal:jurisdiction`. Each
   classification could declare its own entity ontology.

7. **What does the existing `extract.code_symbols.v1` actually produce
   per file?** Read a few generated `file` entity JSONs from a code
   ingest. Confirm the implementation matches the one-entity-per-file
   description in § 4 above. Check whether anything more than
   `type/name/canonical_key/source_path` is present — if so, figure out
   what fills those extra fields and whether the symbol-extraction
   framing was partially implemented and abandoned.

8. **Is tree-sitter a viable dependency for auditgraph?** tree-sitter
   is the obvious cross-language parser foundation for real code
   structure understanding, but it's a C extension and pulls in per-
   language grammar packages. Measure: install footprint, startup
   cost, whether it works on the auditgraph target platforms (Linux
   x86_64 and macOS Intel/Apple Silicon per the README). If tree-
   sitter is unacceptable, the fallback is Python-stdlib `ast` for
   Python and no code-structure support for other languages in v1 —
   which is worth a scope discussion before any implementation.

9. **How does Python-stdlib `ast` handle the real auditgraph codebase?**
   A prototype: write a 50-line script that walks `auditgraph/` with
   `ast.parse` and prints every function and class it finds. Verify
   it handles all the edge cases actually present in the codebase:
   nested functions, methods, decorators, async defs, type-annotated
   signatures, `if TYPE_CHECKING` blocks, conditional imports. If any
   of these fail, document the failure mode.

## Why this is deferred and not urgent

These improvements compound the value of auditgraph for users with
diverse content, but the project's MVP value can be delivered with a
single-document-type model. Issue 3 Phase 2 + Phase 3 (markdown noise
stripping + post-extraction filter) get us 70% of the quality
improvement on the most common content type for ~3 hours of work. A
full document classification system is multi-week effort and should
wait until:

- The current quality fixes have been validated end-to-end
- There is real demand from users with mixed-content workspaces
- The user has thought through the classification taxonomy (the
  `primary_type` enum above is a starting point, not a final list)
- There is a candidate non-spaCy or larger spaCy model that justifies
  the loading overhead

## Pre-requisites the spec should call out

1. Issue 3 Phase 2 (markdown noise stripping) should be in place — it
   becomes the prototype for "noise_stripper: markdown_basic".
2. Issue 3 Phase 3 (post-extraction filter) should be in place — it
   becomes the per-classification "validation pass".
3. The Spec 023 filter framework should be merged — query support for
   `--where "classification=research_paper"` requires it.
4. A representative test corpus should exist — a folder containing one
   research paper, one ADR, one personal note, one PDF scan, one
   contract, one transcript. Without this, classifier rules can't be
   tested.

## Open questions

- **Classifier taxonomy**: who chooses the categories? Hardcoded?
  Configurable? Discoverable from content?
- **Classification confidence**: what happens to documents that don't
  classify cleanly into any category? Default fallback? Human review
  queue?
- **Schema versioning**: classifications add a new field to documents.
  Existing workspaces would need migration or backwards-compat
  handling.
- **Backwards compatibility**: should classification be off by default
  (matching current behavior) or on by default (better quality but
  changes outputs)? Probably off-by-default opt-in initially.
- **Model storage**: where do downloaded models live? Inside `.pkg/`?
  Inside `~/.cache/auditgraph/`? In the user's spaCy default path?
- **Cross-model entity merging**: if `en_core_web_sm` finds "Whisper"
  as PERSON and `en_core_sci_sm` finds "Whisper" as METHOD, are these
  the same entity or different? Canonical key conflict resolution.
- **Chunker ergonomics**: the chunker interface today is `chunk_text(text,
  size, overlap)`. A document-classified chunker needs more
  context — at minimum it needs document type and structural metadata.
  Possibly a context object.
- **Auditgraph's scope on code**: is auditgraph a code intelligence
  tool or a document + provenance tool that happens to tolerate code
  files? The README currently describes it as the latter. Section 4
  above sketches a real code-structure extractor, which would move
  auditgraph meaningfully into the former territory. The answer
  determines whether spec 024 includes per-symbol code entities or
  leaves code at the current one-entity-per-file shallow depth. If
  auditgraph commits to code intelligence, it also takes on ongoing
  per-language parser maintenance and competition with established
  tools (LSP, ctags, tree-sitter-based analyzers, IDE indexers). If
  it doesn't, the `ingestion.chunk_code.enabled` flag from the quality
  sweep is the intended ceiling and § 4 is out of scope forever.
- **Code entity merging with git provenance**: if a code:function
  entity exists for `load_ner_model`, and git provenance has
  `modifies` edges from commits to `file` entities, should the
  granularity also extend down to functions? "Who last modified
  `load_ner_model`?" is a useful question, but answering it requires
  per-line blame → symbol mapping, which is significantly harder than
  per-file modifies edges. Worth a dedicated discussion during spec
  writing.
- **Chunks vs entities for code**: does a code:function need its own
  chunk (with text field = function body) AND its own entity, or can
  the entity itself carry the body text? Documents today have both a
  document record AND chunk records; code could follow the same
  pattern or could collapse them. Cleaner on one side, more work on
  the other.

## When to revisit

Run `/speckit.specify` against this when:

1. A user demand has been validated (the user has actually hit a case
   where mixed-content NER quality blocked their workflow)
2. The current single-pipeline fixes (Issue 3 Phases 1-3) have shipped
   and have measurable quality improvements
3. There is at least one candidate alternative spaCy model installed
   and benchmarked against the current default
4. There is a representative mixed-content test corpus to validate
   against
5. The scope question in Open Questions (auditgraph as code
   intelligence tool vs. document + provenance tool) has been
   answered. If the answer is "document tool only", § 4 of these
   notes is out of scope and the spec should only cover items 1-3
   and 5. If the answer is "code intelligence too", § 4 is in
   scope and the spec must include per-language parser choice,
   new code entity types, and new code link types.
