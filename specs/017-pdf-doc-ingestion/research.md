# Research: PDF and DOC Ingestion

**Feature**: PDF and DOC Ingestion  
**Date**: 2026-02-18  
**Status**: Complete

## R1: PDF extraction backend

**Decision**: Use `pypdf` for day-1 text-layer PDF extraction.

**Rationale**:
- Python-native and easy to integrate into existing CLI pipeline.
- Deterministic for text-layer extraction with stable page iteration.
- No external service dependency required.

**Alternatives considered**:
- `pdfplumber`: richer layout detail but heavier abstraction than needed for day-1.
- `PyMuPDF`: high capability but additional complexity and binary dependency surface.

## R2: DOCX extraction backend

**Decision**: Use `python-docx` for DOCX paragraph/section extraction in document order.

**Rationale**:
- Mature parser for OOXML text extraction.
- Supports ordered traversal needed for deterministic provenance.
- Minimal implementation risk for day-1 scope.

**Alternatives considered**:
- Manual OOXML XML parsing: lower dependency count but high implementation complexity and test burden.

## R3: `.doc` support policy

**Decision**: Exclude `.doc` from day-1.

**Rationale**:
- Converter dependency introduces platform variability and determinism risk.
- User clarification explicitly scoped day-1 to `.pdf` and `.docx`.

**Alternatives considered**:
- Conditional converter path (libreoffice/unoconv): deferred to follow-up feature.

## R4: OCR policy

**Decision**: OCR modes supported in config (`off|auto|on`) with default `off`; OCR execution only when explicitly enabled.

**Rationale**:
- Aligns with determinism and operational predictability.
- Keeps day-1 baseline reliable while preserving opt-in expansion path.

**Alternatives considered**:
- `auto` default: better convenience but more non-deterministic behavior by default.
- `on` default: unnecessary overhead and noise for text-layer PDFs.

## R5: Chunking + citation format

**Decision**: Token-based canonical chunking with token overlap; citation metadata stored in fields only (no inline markers).

**Rationale**:
- Token-based sizing aligns with retrieval behavior and future embedding compatibility.
- Metadata-only citations keep chunk text clean and avoid downstream parser noise.

**Alternatives considered**:
- Character-based chunking: simpler but lower semantic consistency.
- Inline markers: easier visual debugging but pollutes retrieval text.

## R6: Incremental behavior + history model

**Decision**: Overwrite-in-place records for current document state; preserve history through run logs + source hash metadata.

**Rationale**:
- Matches current auditgraph pipeline model.
- Avoids new revision-entity complexity in day-1.

**Alternatives considered**:
- First-class revision entities: deferred due to schema and migration overhead.

## Summary

All high-impact ambiguities are resolved. Day-1 implementation is constrained to deterministic `.pdf`/`.docx` ingestion with provenance, token chunking, metadata-only citations, and compatibility with existing query/export/sync workflows.
