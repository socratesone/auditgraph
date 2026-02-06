# Testing & Quality Gates

## Purpose
Define test matrix, determinism checks, and performance gates.

## Source material
- [SPEC.md](SPEC.md) Testing Strategy
- [SPEC.md](SPEC.md) Non-Functional Requirements

## Decisions Required
- Unit test coverage scope and fixtures.
- Integration and golden test fixtures.
- Determinism regression gates.
- Performance test targets and tooling.

## Decisions (filled)

### Unit Tests

- Required for all domain logic
- Use deterministic fixtures

### Integration/Golden Tests

- Golden fixtures for ingest, extract, link, index
- Run-to-run comparisons for determinism

### Determinism Gates

- Byte-for-byte output comparison for identical inputs
- Stable ordering checks for equal-score queries

### Performance Tests

- Keyword search p50 < 50ms, p95 < 200ms on small datasets
- Graph traversal and why-connected < 1s

## Resolved

- Unit/integration scope, determinism gates, and performance targets defined

## Resolved
- None yet.
