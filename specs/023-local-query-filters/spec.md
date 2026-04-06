# Feature Specification: Local Query Filters & Aggregation

**Feature Branch**: `023-local-query-filters`
**Created**: 2026-04-06
**Status**: Draft
**Input**: User description: "Add deterministic local-first filtering, sorting, pagination, and aggregation primitives to AuditGraph query layer for CLI and MCP"

## Clarifications

### Session 2026-04-06

- Q: What is the current query surface? → 22 MCP tools, each purpose-built. No ad-hoc filter, sort, or aggregation primitives exist. `keyword_search` is the only search function; it does exact-token BM25 lookup plus O(N) chunk substring scan.
- Q: What are the storage access patterns? → All loaders are eager, uncached, and unfiltered. `load_entities()` opens 123K+ files with no type partitioning. `load_links()` does not exist. `load_adjacency()` loads the entire map every call.
- Q: Are there any existing filter-like operations? → Zero reusable filter primitives. The only filtering is domain-specific inline code (e.g., `fnmatch` in git selector, substring match in chunk scan).
- Q: How many entity types exist? → 13 types across NER, git provenance, and content domains.
- Q: How many link types exist? → 7 types across NER co-occurrence and git provenance domains.
- Q: What is the adjacency index state? → Effectively empty (2 bytes) across all profiles. Forward adjacency must be rebuilt as a prerequisite.
- Q: How should `--where` predicates behave on array-valued fields (e.g., `aliases`, `parent_shas`)? → `=` checks array membership; `~` checks if any element contains the substring; comparison operators (`>`, `<`, `>=`, `<=`) exclude the entity (same as missing field).
- Q: When `--count` and `--limit` are combined, does count reflect pre-limit or post-limit? → Count always reflects total matches before limit/offset is applied, consistent with MCP `total_count` semantics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filter Entities by Type (Priority: P1)

As an engineer querying my knowledge graph, I can filter entities by type (e.g., "show all commits" or "show all ner:person entities"), so that I can explore a specific category without scanning the entire graph.

**Why this priority**: Type filtering is the most fundamental query primitive. Every downstream feature (aggregation, sorted results, CLI exploration) depends on it. Without a type index, filtering 123K entities requires a full scan.

**Independent Test**: Given a workspace with entities of types `commit`, `ag:file`, and `ner:person`, when I run `auditgraph list --type commit`, then only `commit` entities are returned in under 2 seconds.

**Acceptance Scenarios**:

1. **Given** a populated workspace, **When** I run `auditgraph list --type ner:person`, **Then** only entities where `type == "ner:person"` are returned.
2. **Given** a populated workspace, **When** I run `auditgraph list --type commit --type ag:file`, **Then** entities matching either type are returned (OR logic).
3. **Given** a workspace with no entities of the requested type, **When** I run `auditgraph list --type ner:law`, **Then** an empty result set is returned (not an error).
4. **Given** the default profile with 123K entities, **When** I run `auditgraph list --type commit`, **Then** the command completes in 2 seconds or less.

---

### User Story 2 - Filter Entities by Field Predicate (Priority: P1)

As an engineer, I can filter entities by field values (e.g., "commits by author X", "entities with mention count above 5"), so that I can narrow results without writing code or post-processing with jq.

**Why this priority**: Field predicates are the second most common query pattern after type filtering. Without them, every query returns everything and the user must filter manually.

**Independent Test**: Given a workspace with commits by multiple authors, when I run `auditgraph list --type commit --where "author_email=alice@example.com"`, then only Alice's commits are returned.

**Acceptance Scenarios**:

1. **Given** commits from two authors, **When** I filter `--where "author_email=alice@example.com"`, **Then** only Alice's commits are returned.
2. **Given** NER entities with varying mention counts, **When** I filter `--where "mention_count>=5"`, **Then** only entities with mention_count 5 or above are returned (numeric comparison).
3. **Given** entities with `authored_at` fields, **When** I filter `--where "authored_at>=2026-01-01"`, **Then** only entities authored on or after that date are returned (string comparison, ISO 8601 lexicographic).
4. **Given** a `--where` clause referencing a nonexistent field, **When** I run the query, **Then** entities lacking that field are excluded from results (not an error).
5. **Given** two `--where` clauses, **When** I run `--where "type=commit" --where "author_email=alice@example.com"`, **Then** both predicates are AND'd together.

---

### User Story 3 - Browse Entities Without a Keyword Query (Priority: P1)

As an engineer, I can browse entities without providing a search term, so that I can explore the graph by type, field, or count without needing to know specific keywords.

**Why this priority**: The current `query` command requires `--q <term>`. There is no way to say "list all commits" or "count entities by type" without a search term. The new `list` command fills this gap.

**Independent Test**: When I run `auditgraph list --type commit`, I get all commit entities without needing to provide a search keyword.

**Acceptance Scenarios**:

1. **Given** a populated workspace, **When** I run `auditgraph list` with no `--q` parameter, **Then** entities are returned (no search term required).
2. **Given** a populated workspace, **When** I run `auditgraph query --q "config" --type ag:file`, **Then** only file entities matching "config" in the BM25 index are returned.
3. **Given** both commands exist, **When** I compare their behavior, **Then** `list` operates on all entities (narrowed by filters) while `query` operates on BM25 search hits (narrowed by filters).

---

### User Story 4 - Filter Neighbors by Edge Type (Priority: P1)

As an engineer navigating the graph, I can filter `neighbors` output by edge type (e.g., "only show `authored_by` edges"), so that I can traverse specific relationship paths without noise from unrelated edges.

**Why this priority**: The current `neighbors` command returns all edge types indiscriminately. For a commit with 50+ `modifies` edges, finding the single `authored_by` edge requires manual scanning.

**Independent Test**: Given a commit node with `modifies`, `authored_by`, and `parent_of` edges, when I run `auditgraph neighbors <commit_id> --edge-type authored_by`, then only the `authored_by` neighbor is returned.

**Acceptance Scenarios**:

1. **Given** a commit with multiple edge types, **When** I filter `--edge-type authored_by`, **Then** only `authored_by` edges and their target nodes are returned.
2. **Given** a node with edges, **When** I filter `--edge-type nonexistent_type`, **Then** an empty neighbor list is returned (not an error).
3. **Given** a commit, **When** I filter `--edge-type modifies --edge-type authored_by`, **Then** edges matching either type are returned (OR logic).
4. **Given** a depth-2 traversal with `--edge-type modifies`, **When** I run the query, **Then** both hops are filtered to `modifies` edges only.
5. **Given** a node with edges of varying confidence, **When** I filter `--min-confidence 0.8`, **Then** only edges with confidence 0.8 or above are returned.

---

### User Story 5 - Sort and Paginate Results (Priority: P1)

As an engineer, I can sort results by a field and limit the count, so that I can find "most recent commits", "top-mentioned entities", or paginate through large result sets.

**Why this priority**: Without sort/limit, queries over 123K entities return unordered bulk data that is unusable in a CLI or MCP context.

**Independent Test**: Given 100 commit entities, when I run `auditgraph list --type commit --sort authored_at --desc --limit 10`, then the 10 most recent commits are returned in descending date order.

**Acceptance Scenarios**:

1. **Given** commit entities with `authored_at`, **When** I sort by `authored_at` descending with `--limit 5`, **Then** the 5 most recent commits are returned in order.
2. **Given** NER entities with `mention_count`, **When** I sort by `mention_count` descending, **Then** the most-mentioned entities appear first.
3. **Given** a `--limit 20 --offset 20` request, **When** I run the query, **Then** results 21-40 are returned (pagination).
4. **Given** a sort field that some entities lack, **When** I sort, **Then** entities without the field are placed last.
5. **Given** two entities with the same sort field value, **When** I sort, **Then** they are ordered by `entity.id` as a stable tiebreaker (determinism guarantee).

---

### User Story 6 - Aggregate Results (Priority: P2)

As an engineer, I can run aggregation queries (count, group-by), so that I can answer questions like "how many entities per type?" or "how many commits per author?" without exporting to another tool.

**Why this priority**: Aggregation is essential for understanding corpus composition but is not blocking entity-level query workflows.

**Independent Test**: Given a workspace with entities of 5 types, when I run `auditgraph list --group-by type --count`, then I get a JSON object mapping each type to its entity count, and the counts sum to the total entity count.

**Acceptance Scenarios**:

1. **Given** a populated workspace, **When** I run `--count`, **Then** a JSON response `{"count": N}` is returned where N is the total matching entity count.
2. **Given** a populated workspace, **When** I run `--group-by type --count`, **Then** a JSON object mapping each type to its count is returned, and values sum to total entity count.
3. **Given** commits with `author_email`, **When** I run `--type commit --group-by author_email --count`, **Then** authors are listed with their commit counts.
4. **Given** a `--group-by` field that some entities lack, **When** I aggregate, **Then** those entities are grouped under a `null` key.

---

### User Story 7 - Filter and Paginate via MCP Tools (Priority: P1)

As an AI assistant using the MCP tools, I can pass filter/sort/limit parameters to `ag_query`, `ag_neighbors`, and a new `ag_list` tool, so that natural language queries can be translated into precise graph operations without flooding the LLM context window.

**Why this priority**: The MCP tools are the primary integration surface for LLM-assisted workflows. Filters must be available here, not just the CLI. Without a default limit, a single query can return 123K entities into an LLM's context window.

**Independent Test**: When I call `ag_list(type="commit", limit=10)`, then at most 10 commit entities are returned, with a `total_count` field indicating the full count.

**Acceptance Scenarios**:

1. **Given** MCP tool `ag_list`, **When** called with `type="commit"` and `sort="authored_at"` and `limit=10`, **Then** the 10 most recent commits are returned.
2. **Given** MCP tool `ag_list`, **When** called with no parameters, **Then** at most 100 results are returned (default limit), with `truncated: true` if total exceeds 100.
3. **Given** MCP tool `ag_query`, **When** called with `type`, `where`, `sort`, `limit` parameters, **Then** filtering is applied server-side before returning results.
4. **Given** MCP tool `ag_neighbors`, **When** called with `edge_type` parameter, **Then** only edges of that type are returned.
5. **Given** any MCP tool returning results, **When** results are truncated, **Then** the response envelope includes `total_count`, `limit`, `offset`, and `truncated` fields.

---

### Edge Cases

- Empty workspace (no entities): all filter/sort/aggregate operations return empty results, not errors.
- `--where` with a nonexistent field: entities lacking that field are excluded (not an error).
- `--type` with a nonexistent type: returns empty results, not an error. The type index file simply does not exist.
- Sort on a field that no entities have: all entities are placed in "missing field" group; stable order by `entity.id`.
- `--group-by` on a field with `null` values or missing entries: grouped under a `null` key in the output.
- `--limit 0`: returns no results (empty list). `--offset` beyond result count: returns empty list.
- `--where` field names are case-sensitive (match JSON key exactly).
- `--where` string values are case-sensitive. `--where "name~Config"` matches "Config" but not "config".
- `--type` values are case-sensitive: `commit` is valid, `Commit` is not.
- `--where` on an array field with `=`: checks membership (e.g., `--where "aliases=config"` matches if `"config"` is in the `aliases` array). `~` checks substring across elements. Comparison operators (`>`, `<`) exclude the entity.

## Constraints

- **Local-first**: All filtering and aggregation MUST work against the local `.pkg` storage. No external database dependency.
- **Deterministic**: Given the same data and query, results MUST be identical across runs, including ordering.
- **Backwards-compatible**: Existing CLI commands and MCP tools MUST continue to work without new parameters. New parameters are additive.
- **Performance budget**: Type-filtered queries over the default profile (~123K entities) MUST complete in under 2 seconds on commodity hardware.
- **No full graph DB dependency**: Neo4j remains optional export target, not a runtime requirement.

## Requirements *(mandatory)*

### Functional Requirements

#### Indexes

- **FR-001**: System MUST maintain a per-type entity index at `indexes/types/<sanitized_type>.json`, where each file contains a JSON array of entity IDs for that type.
- **FR-002**: System MUST maintain a per-type link index at `indexes/link-types/<sanitized_type>.json`, where each file contains a JSON array of link IDs for that type.
- **FR-003**: System MUST rebuild both indexes during the `index` pipeline stage.
- **FR-004**: Filename sanitization MUST replace non-alphanumeric characters with underscores (e.g., `ner:person` becomes `ner_person.json`).

#### Storage APIs

- **FR-010**: System MUST provide `load_entities_by_type(pkg_root, entity_type)` returning an iterator of entity dicts, loading only from the type index.
- **FR-011**: System MUST provide `load_links(pkg_root)` returning an iterator of link dicts.
- **FR-012**: System MUST provide `load_links_by_type(pkg_root, link_type)` returning an iterator of link dicts, loading only from the link-type index.
- **FR-013**: Type-filtered queries MUST NOT load all entities into memory. The type index MUST enable selective loading.
- **FR-014**: All storage iterators MUST return generators (not materialized lists) to support streaming over large collections.

#### Filtering

- **FR-020**: The `query` and `list` CLI commands MUST accept `--type <type>` to filter results by entity type. Multiple `--type` flags MUST be OR'd.
- **FR-021**: The `query` and `list` CLI commands MUST accept `--where "field<op>value"` for field-level predicates. Supported operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~` (substring contains). Multiple `--where` clauses MUST be AND'd.
- **FR-022**: The `neighbors` CLI command MUST accept `--edge-type <type>` to filter edges. Multiple values MUST be OR'd.
- **FR-023**: The `neighbors` CLI command SHOULD accept `--min-confidence <float>` to filter edges by minimum confidence score.
- **FR-024**: Where-clause syntax (v1) MUST support flat top-level fields only. Nested/dotted path access is deferred to a future version.
- **FR-025**: Value type coercion: values matching the pattern `^-?\d+(\.\d+)?$` MUST be compared numerically. All other values MUST be compared as strings.
- **FR-026**: Where-clause parser MUST scan for the first occurrence of a multi-character operator (`>=`, `<=`, `!=`), then single-character (`>`, `<`, `=`, `~`). Everything before the operator is the field name; everything after is the value.
- **FR-027**: When a `--where` predicate targets an array-valued field: `=` MUST check array membership (value exists in the array); `!=` MUST check that the value is NOT a member of the array; `~` MUST check if any element contains the substring; comparison operators (`>`, `<`, `>=`, `<=`) MUST exclude the entity (treated as missing field).

#### Sorting and Pagination

- **FR-030**: The `query` and `list` CLI commands MUST accept `--sort <field>` and `--desc` to control result ordering. Default sort order is ascending.
- **FR-031**: The `query` and `list` CLI commands MUST accept `--limit <N>` and `--offset <N>` for pagination.
- **FR-032**: Sort MUST be stable with a secondary tiebreaker on `entity.id` to guarantee deterministic ordering.
- **FR-033**: Entities missing the sort field MUST be placed last in the result set.

#### Aggregation

- **FR-040**: The `query` and `list` CLI commands SHOULD accept `--count` to return only the count of matching results as `{"count": N}`.
- **FR-041**: The `query` and `list` CLI commands SHOULD accept `--group-by <field>` to group results and return per-group counts as `{"groups": {"value": count, ...}}`.
- **FR-042**: Entities lacking the `--group-by` field MUST be grouped under a `null` key.
- **FR-043**: When `--count` is combined with `--limit` or `--offset`, the count MUST reflect total matches before limit/offset is applied, consistent with the MCP `total_count` semantics (FR-063).

#### New CLI Command

- **FR-050**: System MUST provide an `auditgraph list` command that lists entities without requiring a keyword query (`--q`). It MUST support `--type`, `--where`, `--sort`, `--desc`, `--limit`, `--offset`, `--count`, and `--group-by`.
- **FR-051**: The existing `auditgraph query` command MUST be extended with `--type`, `--where`, `--sort`, `--desc`, `--limit`, `--offset`, `--count`, and `--group-by` parameters.
- **FR-052**: The existing `auditgraph neighbors` command MUST be extended with `--edge-type` and `--min-confidence` parameters.

#### MCP Tools

- **FR-060**: System MUST expose a new `ag_list` MCP tool with parameters: `type`, `where`, `sort`, `limit`, `offset`, `count`, `group_by`.
- **FR-061**: The `ag_query` MCP tool MUST be extended with optional `type`, `where`, `sort`, `limit`, and `offset` parameters.
- **FR-062**: The `ag_neighbors` MCP tool MUST be extended with optional `edge_type` and `min_confidence` parameters.
- **FR-063**: MCP response envelope MUST include `results`, `total_count`, `limit`, `offset`, and `truncated` fields. `total_count` is the count before slicing. `truncated` is `true` when `total_count > limit`.
- **FR-064**: MCP tools MUST default to `limit=100` when no limit is specified. CLI commands MUST default to unlimited.

#### Prerequisites

- **FR-070**: The forward adjacency index (`indexes/graph/adjacency.json`) MUST be rebuilt and populated before filter features ship. The current state is effectively empty.

### Key Entities

- **TypeIndex**: Per-type files at `indexes/types/<sanitized_type>.json`. Each contains a JSON array of entity IDs. Rebuilt during `index` stage.
- **LinkTypeIndex**: Per-type files at `indexes/link-types/<sanitized_type>.json`. Each contains a JSON array of link IDs. Rebuilt during `index` stage.
- **FilterPredicate**: Parsed representation of a `--where` clause: `{field, operator, value, is_numeric}`.
- **QueryPlan**: Internal representation of a query: `{types, predicates, sort, limit, offset, aggregation}`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `auditgraph list --type commit` over the default profile (~123K entities) completes in 2 seconds or less.
- **SC-002**: `auditgraph list --type commit --where "author_email=alice@example.com" --sort authored_at --desc --limit 10` returns correct, ordered results matching only Alice's commits.
- **SC-003**: `auditgraph list --group-by type --count` returns counts that sum to the total entity count in the workspace.
- **SC-004**: `ag_list(type="commit", sort="authored_at", limit=10)` via MCP returns the same results as the equivalent CLI command.
- **SC-005**: All existing CLI commands and MCP tools work without regression when no new parameters are passed.
- **SC-006**: `auditgraph neighbors <id> --edge-type authored_by` returns only `authored_by` edges and no other edge types.
- **SC-007**: The type index is automatically rebuilt when `auditgraph index` runs, with one file per entity type.

## Assumptions

- Entity JSON files are well-formed and all have `id` and `type` fields.
- The `index` pipeline stage runs after `extract` and before `query` in normal workflows, so indexes are up-to-date at query time.
- ISO 8601 date strings sort correctly via lexicographic string comparison.
- The forward adjacency index will be populated as part of this work (FR-070), resolving the current empty state.
- Top-level entity fields cover the practical query space for v1. Nested/dotted path access can be added without breaking changes in a future version.

## Out of Scope (v1)

- Full query language (Cypher, SPARQL, or custom DSL).
- Reverse adjacency index (inbound traversal) -- deferred to a future spec, but this spec's design should not preclude it.
- Semantic/vector search.
- Cross-profile queries -- each profile remains isolated.
- Join-like operations across entity types.
- Bulk write/update via filter expressions.
- Nested/dotted field path access in `--where` clauses.
