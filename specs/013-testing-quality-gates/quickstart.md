# Quickstart: Testing and Quality Gates

**Branch**: 013-testing-quality-gates  
**Date**: 2026-02-11  
**Spec**: [specs/013-testing-quality-gates/spec.md](spec.md)

This quickstart describes the intended workflow for running tests, determinism checks, and performance gates.

## 1) Run unit and integration tests

```bash
pytest -q
```

## 2) Run determinism checks

```bash
pytest -q tests/test_spec013_determinism.py
```

Expected behavior:
- Running the determinism suite twice produces byte-identical outputs.
- Ordering mismatches fail with explicit diffs.

## 3) Run performance gates

```bash
pytest -q tests/test_spec013_performance.py
```

Expected behavior:
- p50/p95 search latency meets NFR-2 targets.
- Incremental ingest+extract for 100 changed files meets NFR-2 targets.
- If thresholds are exceeded by >10%, tests fail with observed values.

## 4) Run quality gate summary

```bash
pytest -q tests/test_spec013_quality_gates.py
```

Expected behavior:
- Failures list the stage, threshold, and observed metrics.
