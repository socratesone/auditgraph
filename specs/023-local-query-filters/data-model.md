# Data Model: Local Query Filters & Aggregation

**Date**: 2026-04-06
**Spec**: [spec.md](spec.md)

## New Artifacts

### TypeIndex

Per-type entity index files.

**Location**: `indexes/types/<sanitized_type>.json`
**Lifecycle**: Rebuilt during `index` pipeline stage. Read-only at query time.
**Format**: JSON array of entity ID strings.

```json
["ent_abc123def456", "ent_789ghi012jkl", ...]
```

**Filename sanitization**: Non-alphanumeric characters replaced with underscores.

| Entity Type | Index Filename | Approx. Size (default profile) |
|-------------|---------------|-------------------------------|
| `ner:person` | `ner_person.json` | ~26K entries |
| `ner:org` | `ner_org.json` | ~42K entries |
| `ner:date` | `ner_date.json` | ~41K entries |
| `commit` | `commit.json` | ~112 entries |
| `file` | `file.json` | ~102 entries |
| `ag:note` | `ag_note.json` | ~21 entries |
| `author_identity` | `author_identity.json` | ~2 entries |
| `repository` | `repository.json` | ~1 entry |

### LinkTypeIndex

Per-type link index files.

**Location**: `indexes/link-types/<sanitized_type>.json`
**Lifecycle**: Rebuilt during `index` pipeline stage. Read-only at query time.
**Format**: JSON array of link ID strings.

```json
["lnk_abc123def456", "lnk_789ghi012jkl", ...]
```

| Link Type | Index Filename | Approx. Size (default profile) |
|-----------|---------------|-------------------------------|
| `CO_OCCURS_WITH` | `co_occurs_with.json` | ~1M entries |
| `MENTIONED_IN` | `mentioned_in.json` | ~500K entries |
| `modifies` | `modifies.json` | varies |
| `parent_of` | `parent_of.json` | varies |
| `authored_by` | `authored_by.json` | varies |
| `contains` | `contains.json` | varies |
| `on_branch` | `on_branch.json` | varies |

### AdjacencyIndex (rebuilt)

Forward adjacency map, rebuilt from all link files.

**Location**: `indexes/graph/adjacency.json` (existing path, new content)
**Lifecycle**: Rebuilt during `index` pipeline stage. Read-only at query time.
**Format**: JSON object mapping source entity ID to list of edge records.

```json
{
  "ent_abc123": [
    {"to_id": "ent_def456", "type": "modifies", "confidence": 1.0, "rule_id": "link.git_modifies.v1"},
    {"to_id": "ent_ghi789", "type": "authored_by", "confidence": 1.0, "rule_id": "link.git_authored_by.v1"}
  ]
}
```

### FilterPredicate

Internal data structure (not persisted).

```python
@dataclass
class FilterPredicate:
    field: str        # e.g., "author_email"
    operator: str     # one of: =, !=, >, >=, <, <=, ~
    value: str        # raw string value from CLI
    is_numeric: bool  # True if value matches ^-?\d+(\.\d+)?$
```

### QueryPlan

Internal data structure (not persisted). Represents the full set of query parameters.

```python
@dataclass
class QueryPlan:
    types: list[str] | None         # --type values (OR'd)
    predicates: list[FilterPredicate] | None  # --where clauses (AND'd)
    sort_field: str | None          # --sort field
    descending: bool                # --desc flag
    limit: int | None               # --limit
    offset: int                     # --offset (default 0)
    count_only: bool                # --count flag
    group_by: str | None            # --group-by field
```

### MCP Response Envelope

Standard response format for all MCP tools returning lists.

```json
{
  "results": [...],
  "total_count": 42157,
  "limit": 100,
  "offset": 0,
  "truncated": true
}
```

- `total_count`: count of all matches before limit/offset applied
- `truncated`: `true` when `total_count > offset + limit`
- `results`: the sliced result list

## Existing Artifacts (unchanged)

### Entity

One JSON file per entity at `entities/<shard>/<entity_id>.json`.

Key fields used by filters:
- `id` (string) — stable SHA256-based identifier, used as sort tiebreaker
- `type` (string) — entity type, used by `--type` filter
- `name` (string) — entity name
- `canonical_key` (string) — normalized key
- `aliases` (array of strings) — used by `--where` with membership semantics
- `author_email` (string, commits only) — used by `--where`
- `authored_at` (string, commits only) — ISO 8601, used by `--where` and `--sort`
- `mention_count` (integer, NER only) — used by `--where` and `--sort`
- `sha` (string, commits only) — git commit SHA

### Link

One JSON file per link at `links/<shard>/<link_id>.json`.

Key fields used by edge-type filtering:
- `id` (string) — link identifier
- `from_id` (string) — source entity ID
- `to_id` (string) — target entity ID
- `type` (string) — link type, used by `--edge-type` filter
- `confidence` (float) — 0.0 to 1.0, used by `--min-confidence` filter
- `rule_id` (string) — provenance rule identifier

## Relationships

```
TypeIndex ──indexes──> Entity (one-to-many, by type)
LinkTypeIndex ──indexes──> Link (one-to-many, by link type)
AdjacencyIndex ──references──> Entity (from_id), Entity (to_id), Link (type, confidence)
FilterPredicate ──applied_to──> Entity fields
QueryPlan ──composes──> FilterPredicate[], types[], sort, pagination, aggregation
```
