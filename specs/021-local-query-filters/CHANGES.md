# Spec 021 — Required Changes

These changes address gaps identified during evaluation. Apply them to `spec.md` in this directory.

---

## Change 1: Add Requirement Traceability (Appendix)

Add a new **Section 20: Requirement Index** at the end (before Final Summary, which becomes Section 21).

This table maps each requirement to an ID for test coverage tracing. Use the existing project convention (`FR-NNN` / `SC-NNN`).

```markdown
## 20. Requirement Index

### Functional Requirements

| ID     | Category   | Requirement                                                                 |
|--------|------------|-----------------------------------------------------------------------------|
| FR-001 | Index      | Maintain per-type entity index at `indexes/types/<sanitized_type>.json`     |
| FR-002 | Index      | Maintain per-type link index at `indexes/link-types/<sanitized_type>.json`  |
| FR-003 | Index      | Rebuild both indexes during `index` pipeline stage                          |
| FR-010 | Storage    | `load_entities_by_type(pkg_root, type) -> Iterator[dict]`                   |
| FR-011 | Storage    | `load_links(pkg_root) -> Iterator[dict]`                                    |
| FR-012 | Storage    | `load_links_by_type(pkg_root, type) -> Iterator[dict]`                      |
| FR-013 | Storage    | Type-filtered queries MUST NOT load all entities into memory                 |
| FR-020 | Filter     | `--type <type>` on `query` and `list`; multiple values OR'd                 |
| FR-021 | Filter     | `--where "field<op>value"` on `query` and `list`; multiple clauses AND'd    |
| FR-022 | Filter     | `--edge-type <type>` on `neighbors`; multiple values OR'd                   |
| FR-023 | Filter     | `--min-confidence <float>` on `neighbors`                                   |
| FR-030 | Sort       | `--sort <field> [--desc]` with stable tiebreaker on `entity.id`             |
| FR-031 | Paginate   | `--limit <N> --offset <N>` on `query` and `list`                            |
| FR-040 | Aggregate  | `--count` returns `{"count": N}`                                            |
| FR-041 | Aggregate  | `--group-by <field>` returns `{"groups": {"value": count, ...}}`            |
| FR-050 | CLI        | New `auditgraph list` command (no `--q` required)                           |
| FR-051 | CLI        | Extended `auditgraph query` with filter/sort/limit params                   |
| FR-052 | CLI        | Extended `auditgraph neighbors` with `--edge-type`, `--min-confidence`      |
| FR-060 | MCP        | New `ag_list` tool with all filter/sort/aggregate params                     |
| FR-061 | MCP        | Extended `ag_query` with `type`, `where`, `sort`, `limit`, `offset`         |
| FR-062 | MCP        | Extended `ag_neighbors` with `edge_type`, `min_confidence`                  |
| FR-063 | MCP        | MCP response envelope: `results`, `total_count`, `limit`, `offset`, `truncated` |
| FR-070 | Prereq     | Forward adjacency index MUST be rebuilt before filter features ship         |

### Success Criteria

| ID     | Criterion                                                                                     |
|--------|-----------------------------------------------------------------------------------------------|
| SC-001 | `auditgraph list --type commit` over default profile (123K entities) completes in ≤ 2s        |
| SC-002 | `auditgraph list --type commit --where "author_email=X" --sort authored_at --desc --limit 10` returns correct, ordered results |
| SC-003 | `auditgraph list --group-by type --count` returns counts summing to total entity count         |
| SC-004 | `ag_list(type="commit", sort="authored_at", limit=10)` returns same results as CLI equivalent |
| SC-005 | All existing CLI commands and MCP tools work without regression when no new params are passed  |
| SC-006 | `auditgraph neighbors <id> --edge-type authored_by` returns only `authored_by` edges          |
| SC-007 | Type index is automatically rebuilt when `auditgraph index` runs                               |
```

---

## Change 2: Define `list` vs `query` Semantics

In **Section 9.1**, after `auditgraph list`, add:

```markdown
### Distinction from `query`

`list` browses entities without requiring a keyword search term.
`query` requires `--q <term>` and applies filters to BM25 search results.

| Command  | Requires `--q`? | Input set                        |
|----------|-----------------|----------------------------------|
| `list`   | No              | All entities (narrowed by filters) |
| `query`  | Yes             | BM25 search hits (narrowed by filters) |
```

---

## Change 3: Specify Numeric Detection Rule

In **Section 8.2**, replace:

```
Numeric detection required (`0.8` vs `"0.8"`)
```

with:

```markdown
#### Value type coercion

Values matching the pattern `^-?\d+(\.\d+)?$` are compared numerically.
All other values are compared as strings.

Examples:
- `--where "mention_count>=5"` → numeric comparison (5, not "5")
- `--where "confidence>=0.8"` → numeric comparison
- `--where "author_email=alice@example.com"` → string comparison
- `--where "authored_at>=2026-01-01"` → string comparison (ISO 8601 sorts lexicographically)
```

---

## Change 4: Specify Quoting and Escaping

In **Section 8.3**, after the `--where` examples, add:

```markdown
#### Quoting rules

The `--where` value is a single shell argument. Use shell quoting to protect it:

```bash
# Standard (shell quotes protect the argument)
--where "author_email=alice@example.com"
--where 'name=foo bar'

# Value containing equals sign: first `=` is the operator, rest is value
--where "name=foo=bar"        # field: name, op: =, value: foo=bar

# Operator precedence: longest match wins
--where "confidence>=0.8"     # field: confidence, op: >=, value: 0.8
--where "name!=test"          # field: name, op: !=, value: test
```

Parser rule: scan for the **first occurrence** of a multi-char operator (`>=`, `<=`, `!=`), then single-char (`>`, `<`, `=`, `~`). Everything before the operator is the field name; everything after is the value.
```

---

## Change 5: Add Concrete Acceptance Tests to Section 15

Replace the current bullet list in **Section 15** with:

```markdown
## 15. Success Criteria

### Acceptance tests

Each test is a runnable command with expected behavior:

| # | Command | Expected |
|---|---------|----------|
| 1 | `auditgraph list --type commit` | Returns only entities with `type=="commit"`; completes in ≤ 2s on default profile |
| 2 | `auditgraph list --type commit --type ag:file` | Returns entities where type is `commit` OR `ag:file` |
| 3 | `auditgraph list --type commit --where "author_email=alice@example.com"` | Returns only commits by Alice |
| 4 | `auditgraph list --type commit --sort authored_at --desc --limit 5` | Returns 5 most recent commits, descending |
| 5 | `auditgraph list --limit 20 --offset 20` | Returns entities 21–40 |
| 6 | `auditgraph list --group-by type --count` | JSON with one key per type; values sum to total entity count |
| 7 | `auditgraph list --count` | `{"count": N}` where N = total entities |
| 8 | `auditgraph neighbors <commit_id> --edge-type authored_by` | Returns only `authored_by` edges |
| 9 | `auditgraph neighbors <commit_id> --edge-type modifies --edge-type authored_by` | Returns edges of either type |
| 10 | `auditgraph list --where "nonexistent_field=x"` | Returns empty result set (not an error) |
| 11 | `auditgraph list --type nonexistent_type` | Returns empty result set (not an error) |
| 12 | `ag_list(type="commit", limit=10)` via MCP | Response includes `total_count`, `truncated`, matches CLI |
| 13 | `ag_list()` via MCP with no params | Returns ≤ 100 results (default limit), `truncated: true` if total > 100 |

### Regression

| # | Command | Expected |
|---|---------|----------|
| 14 | `auditgraph query --q "config"` (no new params) | Identical output to current behavior |
| 15 | `auditgraph neighbors <id>` (no new params) | Identical output to current behavior |

### Case sensitivity

- `--where` field names are **case-sensitive** (match JSON key exactly)
- `--where` string values are **case-sensitive**
- `--where "name~Config"` matches `"Config"` but not `"config"`
- `--type` values are **case-sensitive** (`commit` not `Commit`)
```

---

## Change 6: Fix `load_links` Signature

In **Section 7**, change:

```python
load_links() -> Iterable[Link]
```

to:

```python
load_links(pkg_root) -> Iterator[dict]
```

All three storage functions should use consistent signatures:

```python
load_entities_by_type(pkg_root: Path, entity_type: str) -> Iterator[dict]
load_links(pkg_root: Path) -> Iterator[dict]
load_links_by_type(pkg_root: Path, link_type: str) -> Iterator[dict]
```

Return `Iterator[dict]` (generator), not `list` — this enables streaming over 1.5M links without holding all in memory.
