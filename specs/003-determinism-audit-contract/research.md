# Research

## Summary
Consolidates determinism and audit contract decisions from the spec. No external research required.

## Decisions

### Determinism Boundaries
- Decision: Extraction outputs, link creation, ranking order, and manifests are deterministic. Summaries/QA are deterministic only if pinned and logged.
- Rationale: Core artifacts must be reproducible; optional LLM steps require replay logs.
- Alternatives considered: Allowing non-deterministic ranking (rejected).

### Failure Modes
- Decision: Failures are recorded as skipped with reasons; no silent drops.
- Rationale: Preserves auditability and trust.
- Alternatives considered: Silent skipping (rejected).

### Audit Artifacts
- Decision: Per-run manifests, provenance edges, config snapshot hash, pipeline version, replay log.
- Rationale: Enables deterministic replay and audit trails.
- Alternatives considered: Manifests without provenance (insufficient).

### Config Immutability
- Decision: Snapshot config per run (hash and stored copy).
- Rationale: Ensures reproducibility when config evolves.
- Alternatives considered: Mutable in-place config (breaks replay).

### Ranking Determinism
- Decision: Stable sorting with deterministic tie-break keys.
- Rationale: Ensures stable query ordering.
- Alternatives considered: Default map iteration ordering (non-deterministic).
