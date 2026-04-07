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
  chunking is meaningless. (Already deferred to "Spec 024-style code
  chunking" — but that's a related concern.)
- **Tables / structured data**: row boundaries matter; chunking by
  token destroys row coherence.
- **Transcripts**: speaker turns matter; cutting mid-turn loses
  speaker attribution.
- **Markdown with frontmatter**: the frontmatter shouldn't be chunked
  at all; it's metadata.

A document classification system would route each document to a
chunker appropriate for its type.

### 4. There's no document type beyond extension

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
