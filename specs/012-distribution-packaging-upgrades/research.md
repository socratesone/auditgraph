# Research: Distribution, Packaging, and Upgrades

**Branch**: 012-distribution-packaging-upgrades  
**Date**: 2026-02-11  
**Spec**: [specs/012-distribution-packaging-upgrades/spec.md](spec.md)

This document captures implementation-relevant decisions for distribution, upgrade behavior, and disk budget enforcement.

## Decisions

### Decision 1: Supported OS targets for day 1
- **Decision**: Linux (x86_64) and macOS (Intel/Apple Silicon) only.
- **Rationale**: Aligns with NFR portability while keeping the compatibility matrix manageable.
- **Alternatives considered**:
  - Include Windows on day 1 (rejected due to path and packaging differences that increase risk).

### Decision 2: Packaging and installation approach
- **Decision**: Publish a Python package that provides a console entrypoint `auditgraph` and requires Python 3.10+.
- **Rationale**: Keeps installation consistent with existing codebase and tooling.
- **Alternatives considered**:
  - Single binary distribution (rejected for day 1 due to added build complexity).
  - Docker-only packaging (rejected because it complicates local-first usage).

### Decision 3: Upgrade and migration behavior
- **Decision**: Treat incompatible artifact schema versions as requiring a rebuild; no destructive migrations.
- **Rationale**: Preserves determinism and avoids rewriting existing artifacts.
- **Alternatives considered**:
  - In-place migration (rejected due to risk of irreversibility and loss of provenance).

### Decision 4: Disk footprint budgets
- **Decision**: Default to a 3x multiplier of ingested source size, warn at 80%, block at 100%.
- **Rationale**: Balances headroom for derived artifacts with predictable limits.
- **Alternatives considered**:
  - Fixed size limits (rejected because workspace sizes vary significantly).
