# Feature Specification: Data Sources and Ingestion Policy

**Feature Branch**: `002-data-sources-ingestion`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Data sources and ingestion policy"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Day-1 Sources Definition (Priority: P1)

As an engineer, I can configure the tool to ingest only approved day-1 sources so that ingestion remains deterministic and predictable.

**Why this priority**: Defines the minimum viable ingestion scope and prevents non-deterministic parsing on day 1.

**Independent Test**: Configure a workspace with mixed files and confirm only the allowed formats are ingested.

**Acceptance Scenarios**:

1. **Given** a workspace with Markdown, plain text, PDFs, and HTML files, **When** ingestion runs, **Then** only Markdown, plain text, and Git working tree files are ingested.
2. **Given** a workspace with unsupported formats, **When** ingestion runs, **Then** unsupported files are reported as skipped with a reason.

---

### User Story 2 - Capture Channels (Priority: P2)

As an engineer, I can run manual import and directory scan ingestion so that I control when the system processes new content.

**Why this priority**: Establishes reliable ingestion without background automation that can introduce OS-specific variance.

**Independent Test**: Run manual import and directory scan on the same workspace and confirm deterministic file lists.

**Acceptance Scenarios**:

1. **Given** a configured workspace root, **When** I trigger a directory scan, **Then** it produces a deterministic list of ingested files.
2. **Given** a manual import command, **When** I specify a target path, **Then** only that path is ingested.

---

### User Story 3 - Normalization Rules (Priority: P3)

As an engineer, I can rely on consistent frontmatter normalization so that metadata is predictable across notes.

**Why this priority**: Ensures metadata consistency without requiring perfect compliance in all notes.

**Independent Test**: Ingest Markdown notes with and without frontmatter and verify normalized fields are present.

**Acceptance Scenarios**:

1. **Given** a Markdown note with frontmatter, **When** it is ingested, **Then** title, tags, project, and status are normalized.
2. **Given** a Markdown note without frontmatter, **When** it is ingested, **Then** missing fields are left empty but ingestion succeeds.

---

### Edge Cases

- When include paths do not exist, ingestion should skip them without failing the run.
- When files have unsupported formats, they should be recorded as skipped with a reason.
- When frontmatter is malformed, ingestion should fall back to best-effort extraction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest Markdown, plain text, and Git working tree files on day 1.
- **FR-002**: The system MUST exclude org-mode, PDFs, DOCX, HTML, email exports, and issue tracker exports from day-1 ingestion.
- **FR-003**: The system MUST not perform OCR or PDF ingestion on day 1.
- **FR-004**: The system MUST support file-level symbol extraction for Python, JavaScript, and TypeScript on day 1.
- **FR-005**: The system MUST not require deep AST call graph extraction in the MVP scope.
- **FR-006**: The system MUST defer structured sources (OpenAPI, Terraform, CI configs, JSON/YAML manifests) for day 1.
- **FR-007**: The system MUST support manual import and directory scan capture channels on day 1.
- **FR-008**: The system MUST not require editor plugins or filesystem watchers on day 1.
- **FR-009**: The system MUST apply a canonical frontmatter schema (title, tags, project, status) for Markdown notes.
- **FR-010**: The system MUST record unsupported sources as skipped with a reason.

## Ingestion Policy Summary

- Day-1 sources: Markdown, plain text, Git working tree files.
- Unsupported formats are skipped with explicit reasons.
- Structured sources (OpenAPI, Terraform, CI configs) are deferred.

## Capture Channels Summary

- Manual import and directory scan only in day 1.
- No editor plugins or file watchers in MVP.

## Normalization Summary

- Canonical frontmatter schema: title, tags, project, status.
- Best-effort extraction when frontmatter is missing or malformed.

### Key Entities *(include if feature involves data)*

- **Source**: An ingested file with path, format type, and parse status.
- **IngestionPolicy**: The set of allowed sources, excluded formats, and capture channels for day 1.
- **FrontmatterSchema**: The canonical metadata fields for Markdown notes (title, tags, project, status).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of ingested files on day 1 are from the approved formats (Markdown, plain text, Git working tree).
- **SC-002**: 100% of unsupported files are reported as skipped with a reason in the ingest summary.
- **SC-003**: A new user can configure day-1 sources and run ingestion in under 5 minutes.
- **SC-004**: At least 95% of Markdown notes with frontmatter produce normalized title, tags, project, and status fields.
