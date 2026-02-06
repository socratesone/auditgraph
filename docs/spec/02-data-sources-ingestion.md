# Data Sources & Ingestion Policy

## Purpose
Define day-1 formats, code languages, structured sources, capture channels, and normalization rules.

## Source material
- [SPEC.md](SPEC.md) B) Data Sources and Formats
- [SPEC.md](SPEC.md) Solution Space: Ingestion

## Decisions Required
- Mandatory day-1 sources (Markdown, org-mode, plain text, Git repos, PDFs, DOCX, HTML, email exports, issue trackers).
- PDF reality (born-digital vs scanned; OCR policy).
- Required code languages and AST depth.
- Structured sources to ingest (OpenAPI, Terraform, CI configs, JSON/YAML manifests).
- Capture channels (directory watch, Git-based, editor plugin, manual import).
- Normalization rules (canonical frontmatter schemas vs best-effort extraction).

## Decisions (to fill)
- Day-1 sources: Markdown, plain text, and Git repositories (working tree). Org-mode, PDFs, DOCX, HTML, email exports, and issue tracker exports are out of scope for day 1.
- PDF handling policy: Not supported in day 1; revisit after deterministic text extraction strategy is pinned.
- Code languages and AST depth: File-level symbol extraction only for Python, JavaScript, TypeScript; no deep AST call graphs in MVP.
- Structured sources: JSON/YAML manifests and CI configs are deferred; no OpenAPI/Terraform ingestion in day 1.
- Capture channels: Manual import via CLI and directory scanning; no editor plugins or filesystem watchers in day 1.
- Normalization rules: Canonical frontmatter schema for Markdown (title, tags, project, status) with best-effort extraction for missing fields.

## Resolved
- Day-1 sources
- PDF handling policy
- Code languages and AST depth
- Structured sources
- Capture channels
- Normalization rules

## Assumptions
- Day-1 scope prioritizes deterministic, plain-text inputs to minimize parser variance.
- AST extraction depth can expand after baseline ingestion and indexing are stable.
- Directory scanning plus CLI import is sufficient for early workflows.
