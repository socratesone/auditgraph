# Feature Specification: Linking and Explainability

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Linking produces deterministic, explainable edges between entities. Day-1 linking uses
a single deterministic rule: link entities that reference the same source file.

## Link Rules (day 1)
- **Rule**: `link.source_cooccurrence.v1`
- **Behavior**: For each source path, create `relates_to` links between all entities that reference it.
- **Authority**: `authoritative`

## Link Artifact Schema
Required fields:
- `id`, `from_id`, `to_id`, `type`, `rule_id`, `confidence`, `evidence`, `authority`

### Evidence
Evidence MUST include:
- `source_path`
- `source_hash`

## Backlinks
Backlinks are computed on demand from the adjacency index. Ordering is deterministic by:
`type`, `rule_id`, `from_id`, `to_id`.

## Outputs
- Link artifacts stored under `.pkg/profiles/<profile>/links/<shard>/<link_id>.json`.
- Adjacency index stored at `.pkg/profiles/<profile>/indexes/graph/adjacency.json`.

## Acceptance Tests
- Two entities referencing the same source produce a deterministic link.
- Link artifacts include rule id and evidence.
- Adjacency index is written and deterministic.

## Success Criteria
- 100% of links include explainability evidence and rule id.
