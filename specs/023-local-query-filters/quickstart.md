# Quickstart: Local Query Filters & Aggregation

## Prerequisites

- Workspace initialized: `auditgraph init --root .`
- Pipeline run completed: `auditgraph run <source_dir>/`
- Indexes built (included in `run`, or manually: `auditgraph index`)

## Basic Usage

### List entities by type

```bash
# All commit entities
auditgraph list --type commit

# All NER person entities
auditgraph list --type ner:person

# Multiple types (OR)
auditgraph list --type commit --type ag:file
```

### Filter by field value

```bash
# Commits by a specific author
auditgraph list --type commit --where "author_email=alice@example.com"

# Entities mentioned 5+ times
auditgraph list --type ner:person --where "mention_count>=5"

# Entities with name containing "config"
auditgraph list --where "name~config"
```

### Sort and paginate

```bash
# Most recent 10 commits
auditgraph list --type commit --sort authored_at --desc --limit 10

# Page 2 (items 11-20)
auditgraph list --type commit --sort authored_at --desc --limit 10 --offset 10
```

### Count and aggregate

```bash
# Total entity count
auditgraph list --count

# Entities per type
auditgraph list --group-by type --count

# Commits per author
auditgraph list --type commit --group-by author_email --count
```

### Filter neighbors by edge type

```bash
# Only authored_by edges from a commit
auditgraph neighbors <commit_id> --edge-type authored_by

# Only modifies edges, depth 2
auditgraph neighbors <commit_id> --edge-type modifies --depth 2

# Edges with high confidence only
auditgraph neighbors <entity_id> --min-confidence 0.8
```

### Extended query (keyword + filters)

```bash
# Search "config" but only in file entities
auditgraph query --q "config" --type ag:file

# Search with sort and limit
auditgraph query --q "authentication" --sort name --limit 5
```

## MCP Usage

All filter parameters are available via MCP tools:

```
ag_list(type="commit", sort="authored_at", limit=10)
ag_list(group_by="type", count=true)
ag_query(q="config", type="ag:file", limit=5)
ag_neighbors(id="ent_abc", edge_type="authored_by")
```

MCP tools default to `limit=100`. Responses include `total_count` and `truncated` metadata.

## Operator Reference

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | Equals (or array membership) | `--where "type=commit"` |
| `!=` | Not equals | `--where "type!=commit"` |
| `>` | Greater than | `--where "mention_count>10"` |
| `>=` | Greater or equal | `--where "confidence>=0.8"` |
| `<` | Less than | `--where "mention_count<5"` |
| `<=` | Less or equal | `--where "authored_at<=2026-01-01"` |
| `~` | Contains substring | `--where "name~config"` |

- Numeric values (matching `^-?\d+(\.\d+)?$`) are compared as numbers
- All other values are compared as strings
- Multiple `--where` clauses are AND'd
- Multiple `--type` values are OR'd
