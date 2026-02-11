# Research: Testing and Quality Gates

**Branch**: 013-testing-quality-gates  
**Date**: 2026-02-11  
**Spec**: [specs/013-testing-quality-gates/spec.md](spec.md)

This document captures implementation-relevant decisions for the testing matrix, determinism fixtures, and quality gates.

## Decisions

### Decision 1: Test matrix scope
- **Decision**: Require unit and integration tests for ingest, extract, link, index, and query.
- **Rationale**: Aligns with SPEC.md testing strategy and prevents stage-level regressions.
- **Alternatives considered**:
  - Unit-only coverage (rejected because it misses integration regressions).

### Decision 2: Determinism fixtures
- **Decision**: Use a fixed fixture repository with golden artifacts; compare outputs byte-for-byte and verify stable ordering.
- **Rationale**: Determinism is a core contract and must be enforced in CI.
- **Alternatives considered**:
  - Hash-only checks (rejected because they can hide ordering differences).

### Decision 3: Performance gate thresholds
- **Decision**: Use NFR-2 p50/p95 thresholds; fail the build if thresholds exceed targets by >10%.
- **Rationale**: Allows minor variance while protecting performance budgets.
- **Alternatives considered**:
  - No performance gates (rejected due to regression risk).

### Decision 4: Gate failure reporting
- **Decision**: Gate results must include stage, threshold, and observed value.
- **Rationale**: Ensures actionable feedback for debugging.
- **Alternatives considered**:
  - Generic pass/fail only (rejected due to lack of clarity).
