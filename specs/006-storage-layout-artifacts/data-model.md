# Data Model: Storage Layout and Artifacts

## Entities

### Artifact Root
- Fields: profile, root_path
- Relationships: contains run manifests and artifact directories

### Source Artifact
- Fields: version, path, source_hash, size, mtime, parser_id, parse_status, skip_reason?
- Relationships: referenced by ingest manifest and provenance records

### Entity Artifact
- Fields: version, id, type, name, canonical_key, aliases[], provenance{}, refs[]
- Relationships: referenced by links, indexes, and claims

### Claim Artifact
- Fields: version, id, type, predicate, object, subject_id?, qualifiers{}, provenance{}
- Relationships: referenced by links and indexes

### Link Artifact
- Fields: version, id, from_id, to_id, type, rule_id, confidence, evidence[], explanation?
- Relationships: referenced by graph indexes and explainability output

### Index Artifact
- Fields: version, index_id, type, build_config_hash, pipeline_version, built_at, inputs_manifest_hash, shards[]
- Relationships: references input manifests and artifact shards

## Validation Rules
- Artifact schemas include explicit version fields.
- IDs are deterministic and derived from canonical inputs.
- Shard directories are derived from the first two characters of the ID suffix.
- Index artifacts must reference the manifests used as inputs.

## State Transitions
- Artifacts are immutable once written; new versions are written under new run IDs.
