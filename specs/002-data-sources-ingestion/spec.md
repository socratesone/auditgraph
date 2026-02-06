# Feature Specification: Data Sources and Ingestion Policy

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Auditgraph ingests local files deterministically using a strict allowlist of extensions.
Day-1 ingestion supports Markdown notes, plain text/log files, and code files from Git working trees.

## Scope
Included:
- Markdown notes with frontmatter normalization.
- Plain text and log files.
- Code files for file-level symbols: Python, JavaScript, TypeScript.
- Capture channels: directory scan and manual import.

Out of scope (day 1):
- PDFs, DOCX, HTML, org-mode, email exports, issue tracker exports.
- OCR and scanned documents.
- Structured sources (OpenAPI, Terraform, CI configs, JSON/YAML manifests).
- Editor plugins and filesystem watchers.

## Requirements

### Functional Requirements
- **FR-001**: The system MUST only ingest files with allowed extensions.
- **FR-002**: The default allowed extensions MUST be: `.md`, `.markdown`, `.txt`, `.log`, `.py`, `.js`, `.ts`, `.tsx`, `.jsx`.
- **FR-003**: Unsupported files MUST be recorded as skipped with a reason of `unsupported_extension`.
- **FR-004**: Ingested files MUST be discovered in deterministic, sorted order by normalized path.
- **FR-005**: Manual import MUST ingest only the target paths provided by the user.
- **FR-006**: Markdown frontmatter MUST be parsed for `title`, `tags`, `project`, `status`.
- **FR-007**: When frontmatter is missing, the frontmatter payload MUST be empty and ingestion MUST still succeed.
- **FR-008**: Source artifacts MUST include parse status and skip reason (if any).

### Non-Functional Requirements
- **NFR-001**: Ingestion results MUST be deterministic for identical inputs and config.

## Configuration
The ingestion policy is derived from the active profile:

- `profiles.<name>.ingestion.allowed_extensions`: list of allowed extensions (overrides defaults).
- `profiles.<name>.include_paths`: directories scanned for ingestion.
- `profiles.<name>.exclude_globs`: glob patterns to skip during discovery.

## Data Outputs

### Source Artifact Schema
Each ingested or skipped file produces a source artifact at:
`.pkg/profiles/<profile>/sources/<source_hash>.json` with required fields:

- `path`, `source_hash`, `size`, `mtime`
- `parser_id`, `parse_status`
- `skip_reason` (only when skipped)
- `frontmatter` (Markdown only, may be empty)

### Ingest Manifest
`.pkg/profiles/<profile>/runs/<run_id>/ingest-manifest.json` MUST include:

- `run_id`, `pipeline_version`, `config_hash`, `inputs_hash`, `outputs_hash`
- `records[]` (path, source_hash, parse_status, skip_reason)
- `ingested_count`, `skipped_count`

## User Scenarios

### Scenario 1: Allowlist enforcement
Given a workspace with Markdown, PDF, and HTML files, when ingestion runs,
then only allowed extensions are ingested and unsupported files are recorded as skipped.

### Scenario 2: Manual import
Given a manual import of a specific path, when import runs, then only that path is ingested.

### Scenario 3: Frontmatter parsing
Given a Markdown file with frontmatter, when ingested, then title/tags/project/status are extracted.

## Acceptance Tests
- Ingest rejects `.pdf` and records `unsupported_extension`.
- File discovery order is deterministic and sorted.
- Frontmatter extraction returns expected fields for Markdown.
- Manual import ignores excluded paths and non-target files.

## Success Criteria
- 100% of unsupported files are reported with a skip reason.
- Repeated runs with identical inputs produce identical manifests.
