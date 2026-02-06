# Implementation Plan: Data Sources and Ingestion Policy

**Branch**: `002-data-sources-ingestion` | **Date**: 2026-02-05 | **Spec**: [specs/002-data-sources-ingestion/spec.md](specs/002-data-sources-ingestion/spec.md)
**Input**: Feature specification from `/specs/002-data-sources-ingestion/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define and implement the deterministic day-1 ingestion policy: allowed sources (Markdown, plain text, Git working tree), excluded formats (PDF/DOCX/HTML/org/email/issue exports), limited capture channels (manual import + directory scan), and a canonical Markdown frontmatter schema with best-effort fallback.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.10+  
**Primary Dependencies**: None required for MVP (stdlib-first); optional: PyYAML for config  
**Storage**: Local filesystem (plain-text artifacts)  
**Testing**: pytest (planned)  
**Target Platform**: Linux and macOS (MVP)  
**Project Type**: Single package (CLI-first)  
**Performance Goals**: Deterministic ingestion over configured roots; p50 < 50ms for small queries (not the focus of this feature)  
**Constraints**: Offline-capable; deterministic outputs; strict day-1 format allowlist; no OCR  
**Scale/Scope**: Small/medium datasets (10k–100k docs)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution defined (template placeholders in `.specify/memory/constitution.md`). No gates enforced.

Post-design check (Phase 1): unchanged; no constitution gates applied.

## Project Structure

### Documentation (this feature)

```text
specs/002-data-sources-ingestion/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
auditgraph/
├── __init__.py
├── cli.py
├── config.py
├── errors.py
├── ingest/
├── normalize/
├── pipeline/
├── storage/
└── utils/

config/
docs/
specs/
```

**Structure Decision**: Single-package Python CLI with repository-level config/docs/specs folders.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
