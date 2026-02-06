# Data Model

## Entities

### Entity
- Fields: id, type, name, canonical_key, aliases?, created_at, updated_at, provenance, refs[]
- Relationships: referenced by Claim.subject_id; linked by Link.from_id/to_id

### Claim
- Fields: id, type, subject_id?, predicate, object, qualifiers{time_start?, time_end?, confidence?, status}, provenance
- Relationships: may reference Entity; can be linked via Link

### Source
- Fields: path, source_hash, size, mtime, parser_id, parse_status, repo metadata
- Relationships: provenance.source_file in Claim; refs in Entity; evidence in Link

### Link
- Fields: id, from_id, to_id, type, rule_id, confidence, evidence[], explanation, pipeline_version, run_id
- Relationships: directed edges between Entity/Claim nodes

### Index Manifest
- Fields: index_id, type, build_config_hash, pipeline_version, built_at, inputs_manifest_hash, shards[], explainability

## Validation Rules
- IDs are deterministic hashes based on canonical inputs.
- All references must point to existing Source/Entity/Claim artifacts.
- Evidence ranges must be valid line ranges within source text.

## State Transitions
- Proposed → accepted/rejected (for LLM-derived or low-confidence items).
- Rebuild updates derived artifacts but preserves source-of-truth notes.
