# Research

## Summary
Consolidates knowledge model decisions from the spec. No external research required.

## Decisions

### Canonical Types
- Decision: Define entity, claim, note, task, decision, event as first-class types.
- Rationale: Ensures predictable graph semantics and queryability.
- Alternatives considered: Free-form types without canonical definitions (rejected).

### Contradiction Handling
- Decision: Record both claims and mark contradictions explicitly.
- Rationale: Preserves history and auditability.
- Alternatives considered: Overwrite older claims (rejected).

### Temporal Facts
- Decision: Support optional validity windows on claims.
- Rationale: Engineering facts change over time.
- Alternatives considered: No temporal support (rejected).

### Confidence Policy
- Decision: Rule-based confidence only in day 1.
- Rationale: Deterministic and auditable.
- Alternatives considered: Model-derived scores (deferred).

### Ontology Strategy
- Decision: Primary namespace with optional secondary namespaces for extensions.
- Rationale: Avoids collisions while enabling growth.
- Alternatives considered: Multiple independent ontologies (deferred).
