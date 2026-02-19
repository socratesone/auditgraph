# Feature Specification: PDF and DOC Ingestion

**Feature Branch**: `017-pdf-doc-ingestion`  
**Created**: 2026-02-18  
**Status**: Draft  
**Input**: User description: "Add deterministic PDF and DOCX ingestion with provenance, optional OCR, and Neo4j-compatible export/sync support"

## Clarifications

### Session 2026-02-18

- Q: How should document revisions be modeled? → A: Overwrite-in-place with hash-based history in logs.
- Q: Should `.doc` be supported in day-1 scope? → A: No; day-1 supports `.pdf` and `.docx` only.
- Q: What should be the default OCR policy for day-1? → A: `off` by default; OCR is explicit opt-in.
- Q: How should citations be represented in chunks? → A: Metadata-only citations; no inline markers in chunk text.
- Q: What is the canonical chunking unit? → A: Token-based chunking with configured token overlap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest PDF and DOCX content (Priority: P1)

As a user, I can ingest directories containing PDF and DOCX files through existing ingestion/import flows and receive usable extracted text artifacts.

**Why this priority**: Without core ingestion coverage for target formats, there is no feature value.

**Independent Test**: Import and ingest a fixture directory with mixed `.pdf` and `.docx` files; verify document artifacts are created and query returns extracted content.

**Acceptance Scenarios**:

1. **Given** a workspace with valid PDF and DOCX files, **When** the user runs import+ingest, **Then** the system produces document-derived artifacts that are queryable.
2. **Given** an unchanged PDF or DOCX file already ingested, **When** ingestion is run again, **Then** the file is deterministically skipped with an explicit skip reason.

---

### User Story 2 - Retrieve with source provenance (Priority: P2)

As a user, I can retrieve document-derived chunks and identify where each result came from (file and location in document).

**Why this priority**: Provenance is required for auditability and trust in retrieved content.

**Independent Test**: Run query after ingestion and verify returned chunks include source path and location metadata (page for PDF, ordered section/paragraph reference for DOCX).

**Acceptance Scenarios**:

1. **Given** ingested document content, **When** the user queries relevant text, **Then** results include chunk text and source location metadata.

---

### User Story 3 - Preserve provenance in exports/sync (Priority: P3)

As a user, I can export/sync ingested document graph data and retain provenance metadata in downstream outputs.

**Why this priority**: Export/sync interoperability is needed for existing graph exploration workflows.

**Independent Test**: Ingest fixtures, run export and Neo4j sync, and verify document-derived nodes/chunks retain source provenance fields.

**Acceptance Scenarios**:

1. **Given** ingested PDF/DOCX artifacts, **When** export/sync commands are executed, **Then** exported/synced graph records include provenance fields for document-derived content.

### Edge Cases

- Encrypted or corrupted documents must fail per-file with structured errors, without aborting the full batch by default.
- OCR-disabled mode (default) must still complete ingestion for files with text layers and report clear skip/failure for image-only pages where text is unavailable.
- Any `.doc` file encountered in day-1 mode must be reported as unsupported with explicit per-file reason metadata.
- Oversized files beyond configured limits must be explicitly skipped or failed with reason metadata.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest `.pdf` and `.docx` files through existing import+ingest workflow.
- **FR-002**: The system MUST NOT include `.doc` ingestion in day-1 scope.
- **FR-003**: The system MUST normalize extracted text deterministically (Unicode NFC, `\n` line endings, stable ordering).
- **FR-004**: The system MUST generate stable identifiers for extracted document units based on canonical content and source location context.
- **FR-005**: The system MUST capture provenance for each extracted unit, including `source_path`, `source_hash`, and location reference.
- **FR-015**: The system MUST keep citation data in metadata fields and MUST NOT inject inline page/paragraph markers into chunk text.
- **FR-016**: The system MUST use token-based chunking as the canonical unit and apply overlap using token-count configuration.
- **FR-006**: For PDF extraction, the system MUST include page-based provenance (at least `page_start`, `page_end` where applicable).
- **FR-007**: For DOCX extraction, the system MUST include deterministic order-based location provenance (section/paragraph order index).
- **FR-008**: The system MUST support OCR policy modes (`off`, `auto`, `on`) through ingestion configuration.
- **FR-014**: The system MUST default OCR policy to `off` in day-1 scope; OCR execution requires explicit opt-in via configuration.
- **FR-009**: The system MUST record extractor identity/version and effective ingestion configuration hash for each ingested document.
- **FR-010**: The system MUST perform deterministic unchanged-file skipping by source hash with explicit skip reason reporting.
- **FR-011**: The system MUST emit structured per-file outcomes (`ok`, `skipped`, `failed`) and preserve batch continuation by default.
- **FR-012**: The system MUST keep document-derived provenance fields available to query and export/sync workflows.
- **FR-013**: The system MUST treat document ingestion updates as overwrite-in-place for the current record and rely on run logs plus source hash metadata for historical traceability.

### Key Entities *(include if feature involves data)*

- **DocumentRecord**: Represents an ingested source document with identity, source metadata, extractor metadata, and config hash.
- **SegmentRecord**: Represents ordered extracted text units with type and location provenance.
- **ChunkRecord**: Represents retrieval units derived from segments, with stable identity and segment references.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-ingesting the same fixture set without file changes produces identical extracted outputs and 100% deterministic skip behavior for unchanged files.
- **SC-002**: 100% of returned document chunks from queries include source path and location citation metadata.
- **SC-003**: Batch ingestion completes even when at least one file fails, and each failed/skipped file includes a machine-readable reason.
- **SC-004**: Export and Neo4j sync complete successfully after document ingestion while preserving provenance fields for document-derived graph records.
