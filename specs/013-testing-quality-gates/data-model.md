# Data Model: Testing and Quality Gates

**Branch**: 013-testing-quality-gates  
**Date**: 2026-02-11  
**Spec**: [specs/013-testing-quality-gates/spec.md](spec.md)

This feature introduces structured representations for test matrices, determinism fixtures, and performance gates.

## Entities

### TestMatrix
Defines required tests by stage.

**Fields**
- `stage` (string): ingest | extract | link | index | query
- `unit_tests` (list[string]): Required unit test identifiers
- `integration_tests` (list[string]): Required integration test identifiers

**Rules**
- Every stage MUST have at least one unit test and one integration test.

---

### DeterminismFixture
Defines fixed inputs and golden outputs for determinism checks.

**Fields**
- `fixture_path` (string): Path to fixture repository
- `golden_outputs` (list[string]): Paths to golden artifacts
- `config_path` (string): Config used for fixture runs

**Rules**
- Outputs MUST be compared byte-for-byte.
- Ordering MUST be verified with deterministic tie-break keys.

---

### PerformanceGate
Defines thresholds for performance checks.

**Fields**
- `metric` (string): keyword_p50 | keyword_p95 | ingest_extract_100_files
- `target` (float): Target threshold
- `allowance` (float): Allowed regression margin (default 0.10)

**Rules**
- Gates fail if observed exceeds target by more than allowance.

---

### QualityGateResult
Represents the outcome of a gate evaluation.

**Fields**
- `status` (string): pass | fail
- `stage` (string): Pipeline stage
- `threshold` (float)
- `observed` (float)
- `message` (string)
