# Data Model: Distribution, Packaging, and Upgrades

**Branch**: 012-distribution-packaging-upgrades  
**Date**: 2026-02-11  
**Spec**: [specs/012-distribution-packaging-upgrades/spec.md](spec.md)

This feature introduces compatibility metadata and disk footprint budgeting for derived artifacts.

## Entities

### ArtifactSchemaVersion
Represents the compatibility version recorded in run and artifact manifests.

**Fields**
- `version` (string): Semantic or monotonic version identifier.
- `compatible_with` (list[string]): Optional list of versions considered compatible.

**Rules**
- Every run manifest MUST include `schema_version`.
- Derived artifact manifests MUST include `schema_version`.

---

### FootprintBudget
Represents the storage policy for derived artifacts and indexes.

**Fields**
- `multiplier` (float): Budget multiplier applied to total ingested source size.
- `warn_threshold` (float): Fraction at which warnings are emitted (default 0.80).
- `block_threshold` (float): Fraction at which new writes are blocked (default 1.00).

**Rules**
- Budget applies to the per-profile `.pkg` directory only.
- Minimum source size for calculations is 1 MB.

## Relationships

- **ArtifactSchemaVersion 1—N Runs**: Each run records a schema version.
- **FootprintBudget 1—N Runs**: Each run is evaluated against the active budget policy.
