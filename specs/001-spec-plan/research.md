# Research

## Summary
This phase consolidates known decisions from [spec.md](specs/001-spec-plan/spec.md) and existing repository context. No external research required.

## Decisions

### Language/Runtime
- Decision: Python 3.10+ (per pyproject.toml).
- Rationale: Existing project scaffolding uses Python packaging and CLI entrypoints.
- Alternatives considered: None (keep existing stack).

### Storage Model
- Decision: Local filesystem with plain-text JSON/JSONL artifacts.
- Rationale: Aligns with determinism and diffability requirements in [SPEC.md](SPEC.md).
- Alternatives considered: Embedded DBs as primary storage (rejected for core).

### Interface
- Decision: CLI-first; optional local UI later.
- Rationale: Matches current repository scaffolding and requirements.
- Alternatives considered: Web-first UI.

### Performance Targets
- Decision: p50 < 50ms, p95 < 200ms for small dataset keyword search; <1s for graph traversal.
- Rationale: Derived from NFR targets in [SPEC.md](SPEC.md).
- Alternatives considered: Looser targets (not aligned with UX goals).
