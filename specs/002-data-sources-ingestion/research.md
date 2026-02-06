# Research

## Summary
Consolidates ingestion policy decisions from the spec. No external research required.

## Decisions

### Day-1 Sources
- Decision: Markdown, plain text, and Git working tree files only.
- Rationale: Deterministic parsing and minimal dependency surface.
- Alternatives considered: PDFs, DOCX, HTML, org-mode, email exports (deferred).

### PDF/OCR Policy
- Decision: No PDF ingestion or OCR on day 1.
- Rationale: OCR introduces non-determinism and dependency variance.
- Alternatives considered: OCR with pinned versions (deferred).

### Code Languages and AST Depth
- Decision: File-level symbol extraction for Python, JavaScript, and TypeScript; no deep AST call graphs in MVP.
- Rationale: Keeps extraction deterministic and lightweight.
- Alternatives considered: Full AST call graphs (deferred).

### Structured Sources
- Decision: OpenAPI, Terraform, CI configs, JSON/YAML manifests deferred on day 1.
- Rationale: Prioritize core ingestion stability before structured parsing.
- Alternatives considered: Early structured ingestion (deferred).

### Capture Channels
- Decision: Manual import and directory scan only; no editor plugins or file watchers in day 1.
- Rationale: Avoid OS-specific watcher edge cases.
- Alternatives considered: Always-on watchers (deferred).

### Frontmatter Normalization
- Decision: Canonical frontmatter schema (title, tags, project, status) with best-effort fallback.
- Rationale: Deterministic metadata while supporting incomplete notes.
- Alternatives considered: Best-effort only (less predictable).
