# Feature Specification: Storage Layout and Artifacts

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
All derived artifacts are stored under a profile-scoped root with deterministic paths
and shard placement for entities, claims, and links.

## Directory Layout
```
.pkg/profiles/<profile>/
├── runs/<run_id>/
│   ├── ingest-manifest.json
│   ├── normalize-manifest.json
│   ├── extract-manifest.json
│   ├── link-manifest.json
│   └── index-manifest.json
├── sources/
├── entities/
├── claims/
├── links/
├── indexes/
└── provenance/
```

## Artifact Paths
- Source: `.pkg/profiles/<profile>/sources/<source_hash>.json`
- Entity: `.pkg/profiles/<profile>/entities/<shard>/<entity_id>.json`
- Claim: `.pkg/profiles/<profile>/claims/<shard>/<claim_id>.json`
- Link: `.pkg/profiles/<profile>/links/<shard>/<link_id>.json`
- Index: `.pkg/profiles/<profile>/indexes/<index_type>/<index_id>.json`

## Sharding Rules
- Shard directory is the first two characters of the id suffix.
- Applies to entities, claims, and links.

## Stable IDs
- IDs are derived from canonical inputs using sha256.
- Prefixes identify type: `ent_`, `clm_`, `lnk_`.

## Acceptance Tests
- Entity shard uses first two characters of id suffix.
- Profile root is `.pkg/profiles/<profile>/`.

## Success Criteria
- 100% of artifacts are written to canonical paths.
