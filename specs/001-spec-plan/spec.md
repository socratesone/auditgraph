# Feature Specification: Auditgraph Planning

## Source of Truth
- [SPEC.md](SPEC.md) for full scope, requirements, architecture, and open questions.
- [docs/spec/00-overview.md](docs/spec/00-overview.md) for the sectioned specification set.
- [docs/spec/01-product-scope-users.md](docs/spec/01-product-scope-users.md) for resolved product/user decisions.

## Summary
Auditgraph is a local-first, deterministic personal knowledge graph (PKG) toolkit for engineers. It ingests plain-text notes and code, deterministically extracts entities and claims, creates explainable typed links, builds hybrid search indexes, and provides CLI-first navigation with optional local UI. The source of truth is plain-text; all derived artifacts are reproducible, diffable, and fully audited.

## Resolved Decisions (current)
- Primary users: solo engineers and small engineering teams (1–8 users).
- Domain scope: software-engineering knowledge with optional personal notes.
- Top workflows: codebase comprehension, debugging logs, ADR capture, search/recall, project planning.
- Query expectations: search/recall with explainable citations plus graph exploration.
- Ingestion volume targets: daily 10–200 files, weekly 100–1,000 files.
- Latency targets: <200ms for search/recall and symbol lookup; <1s for graph traversal and “why connected”.
- Manual review budget: up to 5 minutes/day.

## Open Decisions
See the open items tracked in [docs/spec/15-open-questions-log.md](docs/spec/15-open-questions-log.md).
