# Implementation Plan: PDF and DOC Ingestion

**Branch**: `001-pdf-doc-ingestion` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-pdf-doc-ingestion/spec.md`

## Summary

Implement day-1 deterministic document ingestion for `.pdf` and `.docx` in the existing auditgraph ingest pipeline. Preserve source provenance as metadata (no inline citation markers), default OCR policy to `off`, and keep exports/sync compatible by ensuring provenance survives through downstream graph artifacts.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: existing `pyyaml`, `pytest`; add `pypdf` (PDF extraction), add `python-docx` (DOCX extraction)  
**Storage**: File-based `.pkg` artifacts (authoritative), existing manifest/audit logs  
**Testing**: `pytest` with unit + fixture/golden + integration tests  
**Target Platform**: Linux/macOS CLI (Windows compatibility via Python runtime)  
**Project Type**: Single CLI project  
**Performance Goals**: deterministic re-ingest outputs; per-file memory bounded by page/paragraph streaming strategy where possible  
**Constraints**: `.doc` out of day-1 scope, OCR default `off`, metadata-only citations, batch should continue on per-file failures  
**Scale/Scope**: day-1 fixture and moderate batch directories; unchanged-file skips by hash

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

| Gate | Status | Justification |
|------|--------|---------------|
| DRY | ✅ PASS | Reuse existing ingest/discovery/manifest/audit infrastructure; add document extractors as adapters |
| SOLID-SRP | ✅ PASS | Separate backend extractors (PDF/DOCX) from normalization/chunking/persistence logic |
| SOLID-DIP | ✅ PASS | Extractor backend abstraction isolates external parser libraries |
| TDD | ✅ PASS | Feature requires fixture-first tests before implementation |
| Simplicity | ✅ PASS | Day-1 excludes `.doc`; OCR opt-in only |

### Post-Design Gate (Re-check)

| Gate | Status | Justification |
|------|--------|---------------|
| DRY | ✅ PASS | Shared segment/chunk model and provenance writer across PDF and DOCX backends |
| SOLID-SRP | ✅ PASS | Compiler/ingest pipeline unchanged; new logic isolated in document extraction adapters |
| SOLID-DIP | ✅ PASS | Parser libs called through backend interface, enabling test doubles |
| TDD | ✅ PASS | Tests explicitly cover determinism, provenance, skip/error behavior, and export/sync continuity |
| Simplicity | ✅ PASS | No `.doc` conversion in day-1; no inline citation markers |

## Project Structure

### Documentation (this feature)

```text
specs/001-pdf-doc-ingestion/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── document-ingestion-contract.yaml
└── tasks.md
```

### Source Code (repository root)

```text
auditgraph/
├── ingest/
│   ├── parsers.py                 # extend extension/parser routing for pdf/docx
│   ├── importer.py                # existing import behavior retained
│   └── manifest.py                # skip/failure reporting integration
├── extract/
│   └── [new document extraction module(s)]
├── storage/
│   ├── artifacts.py               # persist document-derived entities/chunks
│   └── manifests.py               # provenance/config-hash integration
└── utils/
    └── [normalization/chunk helpers if needed]

config/
└── pkg.yaml                       # include `.pdf`/`.docx`, OCR/chunk settings

tests/
├── fixtures/
│   └── documents/
│       ├── sample.pdf
│       ├── scanned.pdf
│       └── sample.docx
├── test_spec017_document_ingestion.py
└── test_spec017_export_sync_provenance.py
```

**Structure Decision**: Single-project CLI architecture. Extend existing ingest pipeline with document extractor backends; do not introduce new service boundary.

## Complexity Tracking

No constitution violations requiring exception.
