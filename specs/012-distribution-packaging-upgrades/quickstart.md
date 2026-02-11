# Quickstart: Distribution, Packaging, and Upgrades

**Branch**: 012-distribution-packaging-upgrades  
**Date**: 2026-02-11  
**Spec**: [specs/012-distribution-packaging-upgrades/spec.md](spec.md)

This quickstart describes the intended workflow for installation, upgrades, and budget enforcement.

## 1) Install and verify

```bash
pip install auditgraph

auditgraph version
```

## 2) Initialize a workspace

```bash
auditgraph init --root .
```

## 3) Configure disk budget (optional)

Update `config/pkg.yaml`:

```yaml
storage:
  footprint_budget:
    multiplier: 3.0
    warn_threshold: 0.80
    block_threshold: 1.00
```

## 4) Run ingest and observe budget behavior

```bash
auditgraph ingest --root . --config config/pkg.yaml
```

Expected behavior:
- Warn when usage reaches 80% of the budget.
- Block new derived artifacts at 100% and print the current usage.

## 5) Upgrade behavior

When schema versions are compatible, commands proceed without warnings.
When incompatible, the CLI instructs you to rebuild and preserves prior runs.
