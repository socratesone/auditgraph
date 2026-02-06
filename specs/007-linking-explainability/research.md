# Research: Linking and Explainability

## Decision 1: Link Generation Policy

- **Decision**: Deterministic rules produce authoritative links; optional suggestion rules are allowed but must be flagged as non-authoritative.
- **Rationale**: Aligns with determinism and audit requirements while allowing optional discovery.
- **Alternatives considered**: Only deterministic rules, no suggestions. Rejected because optional suggestions are part of the roadmap.

## Decision 2: Supported Link Types

- **Decision**: Support mentions, defines, implements, depends_on, decided_in, relates_to, cites.
- **Rationale**: Matches the current linking decisions in clarifying answers and spec.
- **Alternatives considered**: Free-form link types without a fixed list. Rejected due to inconsistent metadata requirements.

## Decision 3: Explainability Payload

- **Decision**: Explainability payload includes rule_id, evidence snippet reference, and scores when applicable.
- **Rationale**: Provides auditability for every link without requiring full-text duplication.
- **Alternatives considered**: Only rule_id. Rejected because evidence is required for trust.

## Decision 4: Backlinks Policy

- **Decision**: Compute backlinks on demand in MVP; store when performance requires it.
- **Rationale**: Reduces storage overhead while keeping deterministic traversal.
- **Alternatives considered**: Always store backlinks. Rejected due to extra storage and rebuild complexity.

## Decision 5: Deterministic Ordering

- **Decision**: Links are ordered by type, then rule_id, then from_id/to_id to ensure stable ordering.
- **Rationale**: Stable sorting guarantees repeatable outputs across platforms.
- **Alternatives considered**: Unordered lists. Rejected because it breaks determinism.
