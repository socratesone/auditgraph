# Research: Storage Layout and Artifacts

## Decision 1: Canonical Directory Layout

- **Decision**: Store derived artifacts under `.pkg/profiles/<profile>/` with run manifests under `.pkg/profiles/<profile>/runs/<run_id>/`.
- **Rationale**: This matches existing pipeline artifacts and enables per-profile isolation.
- **Alternatives considered**: Single shared `.pkg/` root without profiles. Rejected due to cross-profile contamination risks.

## Decision 2: Artifact Schemas

- **Decision**: Define schemas for sources, entities, claims, links, and indexes with required fields and version identifiers.
- **Rationale**: Stable schemas enable deterministic diffing and external tooling.
- **Alternatives considered**: Free-form JSON without versioning. Rejected due to audit ambiguity.

## Decision 3: Sharding Rules

- **Decision**: Use a two-character ID prefix for shard directories (e.g., `ent_ab...` stored under `entities/ab/`).
- **Rationale**: Simple, deterministic sharding keeps directories small without complex indexing.
- **Alternatives considered**: No sharding or hash-based bucket counts. Rejected due to filesystem scaling concerns.

## Decision 4: Stable ID Canonicalization

- **Decision**: Stable IDs are derived from canonical inputs and hashed with sha256. Canonicalization uses normalized paths and stable text forms.
- **Rationale**: Matches determinism requirements and existing hashing utilities.
- **Alternatives considered**: UUIDs or runtime counters. Rejected due to non-determinism.

## Decision 5: Versioning Rules

- **Decision**: All artifact schemas include explicit `version` fields; changes require version bumps and run-level compatibility notes.
- **Rationale**: Makes schema evolution explicit and auditable.
- **Alternatives considered**: Implicit versioning via field presence. Rejected because it complicates tooling.
