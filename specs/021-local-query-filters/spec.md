```markdown
# 021 — Local Query Filters & Aggregation (Final Spec)

## 1. Objective

Add **deterministic, local-first filtering, sorting, pagination, and aggregation primitives** to AuditGraph’s query layer, enabling:

- Efficient CLI exploration of the knowledge graph
- Structured MCP (Model Context Protocol) access for LLM workflows
- Elimination of full-scan query patterns over entity/link storage

---

## 2. Hard Constraints

- **Local-first**: All operations execute against `.pkg` storage only
- **Deterministic**: Same input → identical output (ordering included)
- **Backwards-compatible**: Existing CLI + MCP tools unchanged unless new params are used
- **Performance target**: Type-filtered queries over ~123K entities ≤ 2s
- **No full graph DB dependency**: Neo4j remains optional export, not runtime requirement

---

## 3. Scope

### Included

- Type filtering
- Field predicates (`--where`)
- Edge-type filtering in traversal
- Sorting + pagination
- Aggregation (`count`, `group-by`)
- New CLI command: `list`
- MCP parity via `ag_list`, extended params

### Excluded (v1)

- Query language (Cypher/SPARQL/DSL)
- Reverse adjacency (inbound traversal)
- Semantic/vector search
- Join-style queries across entity types
- Bulk write/update via filters

---

## 4. Architecture

### Layered Model

```

Indexes
↓
Storage access (selective loading)
↓
Query engine (filter, sort, aggregate)
↓
CLI interface
↓
MCP interface

```

---

## 5. Data Model Context

- Entities: one JSON file per entity
- Links: one JSON file per edge
- Graph: implicit via links + adjacency index
- IDs: stable SHA256-based identifiers

---

## 6. Index Strategy

### 6.1 Entity Type Index

**Location:**
```

indexes/types/<sanitized_type>.json

````

**Format:**
```json
["ent_<id1>", "ent_<id2>", ...]
````

**Example:**

```
indexes/types/commit.json
indexes/types/ner_person.json
```

### 6.2 Link Type Index

**Location:**

```
indexes/link-types/<sanitized_type>.json
```

**Reasoning:**

* Links scale to millions → must avoid monolithic files
* Enables selective loading

### 6.3 Filename Sanitization

| Original     | Stored            |
| ------------ | ----------------- |
| `ner:person` | `ner_person.json` |

---

## 7. Storage APIs

### Required

```python
load_entities_by_type(pkg_root, type) -> Iterable[Entity]
load_links() -> Iterable[Link]
load_links_by_type(pkg_root, type) -> Iterable[Link]
```

### Constraints

* MUST NOT load all entities for type-filtered queries
* MUST stream or batch load when possible

---

## 8. Query Engine

### 8.1 QueryPlan

Internal representation:

```json
{
  "types": [...],
  "predicates": [...],
  "sort": {...},
  "limit": N,
  "offset": N,
  "aggregation": {...}
}
```

---

### 8.2 Filtering

#### Type filter

* `--type` supports multiple values (OR)

#### Field predicates

Syntax:

```
field<op>value
```

Supported operators:

| Operator     | Meaning                   |
| ------------ | ------------------------- |
| =            | equality                  |
| !=           | inequality                |
| >, >=, <, <= | numeric/string comparison |
| ~            | substring contains        |

#### Behavior

* Multiple `--where` clauses = AND
* Missing field = excluded (not error)
* Numeric detection required (`0.8` vs `"0.8"`)

---

### 8.3 Where Syntax (v1)

**Flat fields only**

Example:

```bash
--where "author_email=alice@example.com"
--where "confidence>=0.8"
```

**Deferred:**

* Nested/dotted paths (future version)

---

### 8.4 Sorting

```
--sort <field>
--desc
```

### Determinism Requirement

Sort must be stable:

```
PRIMARY: requested field
SECONDARY: entity.id
```

Missing fields:

* Sorted last

---

### 8.5 Pagination

```
--limit N
--offset N
```

Defaults:

* CLI: unlimited
* MCP: default limit = 100

---

### 8.6 Aggregation

#### Count

```
--count
```

Returns:

```json
{
  "count": N
}
```

#### Group-by

```
--group-by <field>
```

Returns:

```json
{
  "groups": {
    "value1": count,
    "value2": count,
    "null": count
  }
}
```

---

## 9. CLI Interface

### 9.1 New Command

```
auditgraph list
```

Supports:

* `--type`
* `--where`
* `--sort`
* `--desc`
* `--limit`
* `--offset`
* `--count`
* `--group-by`

---

### 9.2 Existing Commands

#### query

Add:

```
--type
--where
--sort
--desc
--limit
--offset
--count
--group-by
```

#### neighbors

Add:

```
--edge-type
--min-confidence
```

---

## 10. MCP Interface

### 10.1 ag_list (new)

Parameters:

```
type
where
sort
limit
offset
count
group_by
```

---

### 10.2 ag_query

Add:

```
type
where
sort
limit
offset
```

---

### 10.3 ag_neighbors

Add:

```
edge_type
min_confidence
```

---

### 10.4 MCP Response Format

```json
{
  "results": [...],
  "total_count": 42157,
  "limit": 100,
  "offset": 0,
  "truncated": true
}
```

### Rules

* Default limit = 100
* `total_count` = count before slicing
* `truncated = total_count > limit`

---

## 11. Adjacency Requirement

### Critical prerequisite

* Forward adjacency index MUST be rebuilt:

```
indexes/graph/adjacency.json
```

### Reason

* Current state: effectively empty
* Without this, traversal is inefficient

---

## 12. Performance Expectations

* Type-filter query: ≤ 2 seconds
* No full scans for filtered queries
* Index rebuild cost acceptable (offline stage)

---

## 13. Edge Cases

* Empty workspace → empty result
* Missing fields → excluded
* Mixed numeric/string comparisons → handled explicitly
* ISO dates → lexicographic comparison valid
* Special characters → require quoting/escaping

---

## 14. Determinism Guarantees

Must guarantee:

* Stable ordering
* No nondeterministic iteration
* Identical outputs across runs

---

## 15. Success Criteria

* Type-filter queries < 2s
* Correct predicate filtering
* Stable sorted output
* Accurate aggregation
* MCP and CLI parity
* No regression in existing commands

---

## 16. Implementation Order

### Phase 1 — Index + Storage

* Type index
* Link-type index
* Storage loaders
* Fix adjacency rebuild

### Phase 2 — Query Engine

* Predicate parsing
* Filter execution
* Sorting
* Pagination
* Aggregation

### Phase 3 — CLI

* `list`
* Extended `query`
* Extended `neighbors`

### Phase 4 — MCP

* `ag_list`
* Extended `ag_query`
* Extended `ag_neighbors`

### Phase 5 — Testing

* Determinism
* Edge cases
* Performance
* Large dataset validation

---

## 17. Open Design Decisions (Resolved)

| Decision          | Outcome                      |
| ----------------- | ---------------------------- |
| Where syntax      | Flat fields (v1), extensible |
| Index format      | Per-type files               |
| MCP default limit | 100 + metadata               |
| Reverse adjacency | Deferred                     |

---

## 18. Future Extensions

* Nested field access (`dot-path`)
* Reverse adjacency index
* Path queries
* Join-like filters
* Vector search integration

---

## 19. Final Summary

This spec introduces a **deterministic, indexed query layer** that transforms AuditGraph from a raw data store into a usable local knowledge graph system, while preserving:

* local-first guarantees
* reproducibility
* CLI-first philosophy
* LLM compatibility via MCP

```
```
