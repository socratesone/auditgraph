# Research: Neo4j Export and Sync

**Feature**: Neo4j Export and Sync  
**Date**: 2026-02-17  
**Status**: Complete

## R1: Neo4j Python Driver Best Practices

**Question**: What patterns are recommended for batched writes, pooling, and transactions with the official Neo4j Python driver?

**Findings**:
- Use official `neo4j` package.
- Prefer `driver.session()` context managers.
- Use write transactions with parameterized Cypher.
- Keep batch size at 1000 records for balanced throughput/memory.
- Use environment variables for connectivity (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).

**Decision**: Use official driver + write transactions + environment-based connection settings.

## R2: Idempotency and Constraints

**Question**: How should idempotent sync be guaranteed?

**Findings**:
- Use `MERGE` keyed by stable auditgraph IDs.
- Ensure unique constraints before sync.
- Use `IF NOT EXISTS` where supported.

**Decision**: Enforce constraints at sync start, then apply `MERGE` for nodes/relationships.

## R3: Export File Format and Batching

**Question**: What output format provides deterministic and importable exports?

**Findings**:
- UTF-8 `.cypher` output is portable.
- `:begin`/`:commit` batches are compatible with `cypher-shell`.
- Deterministic ordering by stable IDs is required.

**Decision**: Single `.cypher` file, deterministic order, batched transactions, MERGE statements.

## R4: Redaction Consistency

**Question**: How should redaction apply to export/sync?

**Findings**:
- Existing redaction utilities already cover required secret classes.
- Export/sync should reuse the same redaction policy path as other artifacts.

**Decision**: Reuse existing redaction pipeline for all Neo4j-bound payloads.

## R5: Error Handling and Resilience

**Question**: What failure modes and diagnostics are required?

**Findings**:
- Handle connectivity, auth, transient transaction, and client errors distinctly.
- Dry-run must validate safely without mutating target DB.

**Decision**: Map Neo4j exceptions to actionable diagnostics and preserve dry-run safety guarantees.

## Summary

Research resolves key unknowns and supports the selected design:
- Export + sync both use MERGE semantics
- Batch size fixed at 1000
- Env-based credentials
- Deterministic ordering and file-based system-of-record preserved
