# Spec 17: PDF and DOC Ingestion (Minimal Contract)

## Goal
Add deterministic ingestion for `.pdf`, `.docx`, and optional `.doc` so document text becomes first-class auditgraph artifacts with provenance.

## Scope
- In scope:
  - ingest PDF and DOCX from existing ingest/import flows
  - optional DOC via explicit conversion step
  - deterministic normalization and chunking
  - provenance per extracted unit (file + location)
  - compatibility with query/export/sync (including Neo4j)
- Out of scope:
  - pixel/layout fidelity
  - advanced table/figure semantics
  - cloud/off-box extraction services

## Required Behavior

### 1) Entry points
- Must work with current project flow:
  - `auditgraph import <paths...> --root . --config config/pkg.yaml`
  - `auditgraph ingest --root . --config config/pkg.yaml`
- `config/pkg.yaml` allowlist must include `.pdf` and `.docx` (and `.doc` only if converter is configured).

### 2) Deterministic extraction
- Given identical input bytes + config, outputs must be identical.
- Enforce:
  - Unicode NFC
  - line endings `\n`
  - stable ordering of segments/chunks
  - stable IDs derived from canonical content and source path

### 3) Provenance
Every extracted unit must include, at minimum:
- `source_path`
- `source_hash`
- location reference:
  - PDF: `page_start`/`page_end`
  - DOCX: paragraph/section order index
- extractor identity/version used for the file

### 4) Backend policy
- PDF text layer extraction is default.
- OCR is optional and must be explicit/config-driven.
- DOCX extraction reads OOXML text in document order.
- DOC support is optional; if converter missing, emit actionable error (no silent fallback).

### 5) Failure and skip rules
- Batch ingestion must continue on per-file failures by default.
- Emit structured result per file: `ok | skipped | failed` with reason.
- Unchanged file hash may be skipped deterministically.

### 6) Persistence and graph integration
- Persist extracted units as standard auditgraph artifacts so downstream normalize/extract/link/index can run unchanged.
- Export paths (`auditgraph export`, `export-neo4j`, `sync-neo4j`) must preserve provenance fields already stored in artifacts.

## Data Contract (Minimal)
For each ingested document:
- Document metadata:
  - stable `document_id`
  - `source_path`, `source_hash`, `mime_type`, `file_size`, `ingested_at`
  - `extractor_id`, `extractor_version`, `ingest_config_hash`
- Segments:
  - stable `segment_id`, `order`, `text`, `type`
  - location fields (page or paragraph index)
- Chunks:
  - stable `chunk_id`, `text`, `order`, source segment references

## Configuration Contract
Add ingestion config keys (or equivalent profile-scoped keys) for:
- enabled extractors per file type
- OCR policy: `off | auto | on`
- chunk size + overlap
- max file size

Effective ingestion config must be hashable and recorded per run.

## Acceptance Criteria
1. Ingesting a directory containing `.pdf` and `.docx` produces deterministic artifacts across repeated runs.
2. Each extracted chunk can be traced back to file + location.
3. Unchanged files are skipped by hash with explicit skip reason.
4. Corrupt/encrypted/unsupported files produce structured errors without aborting whole batch.
5. Export and Neo4j sync succeed with provenance-bearing document nodes/chunks present.

## Test Minimum
- Unit:
  - normalization determinism
  - stable ID generation
  - backend selection logic
- Fixture/golden:
  - one text PDF
  - one scanned/no-text PDF
  - one DOCX with headings/lists/tables
- Integration:
  - ingest -> query returns chunk text + citation metadata
  - ingest -> export-neo4j/sync-neo4j does not drop provenance fields

