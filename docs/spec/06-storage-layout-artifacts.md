# Storage Layout & Artifact Schemas

## Purpose
Finalize directory layout, artifact schemas, shard rules, and stable ID mechanics.

## Source material
- [SPEC.md](SPEC.md) Storage layout, Stable IDs, Example artifacts

## Decisions Required
- Final directory structure and naming conventions.
- Artifact schemas (sources, entities, claims, links, indexes).
- Sharding rules (prefix length, shard size caps).
- Stable ID canonicalization rules and versioning.

## Decisions (filled)

### Directory Structure

Storage root is profile-scoped under `.pkg/profiles/<profile>/`.

```
.pkg/profiles/<profile>/
├── runs/<run_id>/
│   ├── ingest-manifest.json
│   ├── normalize-manifest.json
│   ├── extract-manifest.json
│   ├── link-manifest.json
│   ├── index-manifest.json
│   └── serve-manifest.json
├── sources/
├── entities/
├── claims/
├── links/
├── indexes/
└── provenance/
```

Artifact paths:

| Artifact | Path pattern |
| --- | --- |
| Source | `.pkg/profiles/<profile>/sources/<source_hash>.json` |
| Entity | `.pkg/profiles/<profile>/entities/<shard>/<entity_id>.json` |
| Claim | `.pkg/profiles/<profile>/claims/<shard>/<claim_id>.json` |
| Link | `.pkg/profiles/<profile>/links/<shard>/<link_id>.json` |
| Index | `.pkg/profiles/<profile>/indexes/<index_type>/<index_id>.json` |

### Artifact Schemas

All artifacts include a `version` field.

Required fields:

- **Source**: `version`, `path`, `source_hash`, `size`, `mtime`, `parser_id`, `parse_status`, `skip_reason` (optional)
- **Entity**: `version`, `id`, `type`, `name`, `canonical_key`, `aliases`, `provenance`, `refs`
- **Claim**: `version`, `id`, `type`, `predicate`, `object`, `provenance`, `subject_id` (optional), `qualifiers` (optional)
- **Link**: `version`, `id`, `from_id`, `to_id`, `type`, `rule_id`, `confidence`, `evidence`, `explanation` (optional)
- **Index**: `version`, `index_id`, `type`, `build_config_hash`, `pipeline_version`, `built_at`, `inputs_manifest_hash`, `shards`

### Sharding Rules

- Shard directory is the first two characters of the ID suffix (e.g., `ent_abcd...` stored under `entities/ab/`).
- Sharding applies to entities, claims, and links.
- Sources and indexes are stored without sharding.

### Stable ID Canonicalization

- Canonical inputs are normalized paths and stable text forms.
- Stable IDs are derived by hashing canonical inputs with sha256.
- ID prefixes identify artifact type (e.g., `ent_`, `clm_`, `lnk_`).
- Canonicalization and schema changes require version bumps.

## Resolved

- Canonical storage root under `.pkg/profiles/<profile>/` with run manifests in `runs/<run_id>/`.
- Artifact schemas and required fields defined for sources, entities, claims, links, and indexes.
- Sharding uses two-character ID prefixes for entities, claims, and links.
- Stable IDs use canonicalized inputs hashed with sha256 and type prefixes.
