# Quickstart: Neo4j Export and Sync

**Feature**: Neo4j Export and Sync  
**Version**: 1.0.0  
**Last Updated**: 2026-02-17

## Prerequisites

- Auditgraph installed and configured (see main [QUICKSTART.md](../../../QUICKSTART.md))
- Python 3.10+
- Neo4j instance (local or remote) for sync operations
- Network connectivity to Neo4j instance (for sync only; export works offline)

## Installation

### 1. Install Neo4j Python Driver

```bash
cd auditgraph
source .venv/bin/activate
pip install neo4j
```

### 2. Verify Installation

```bash
python -c "import neo4j; print(f'neo4j driver version: {neo4j.__version__}')"
```

Expected output: `neo4j driver version: 5.x.x` (or 4.x.x)

## Quick Start: Export

### 1. Ensure You Have Graph Data

```bash
# If starting fresh, run a full pipeline
auditgraph rebuild --root . --config config/pkg.yaml
```

This creates entities and links in `.pkg/profiles/default/`.

### 2. Export to Cypher File

```bash
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/graph.cypher
```

**Output**:
```json
{
  "mode": "export",
  "profile": "default",
  "output_path": "/path/to/auditgraph/exports/neo4j/graph.cypher",
  "nodes_processed": 42,
  "relationships_processed": 87,
  "skipped_count": 0,
  "failed_count": 0,
  "duration_seconds": 0.234
}
```

### 3. Inspect Generated File

```bash
head -n 20 exports/neo4j/graph.cypher
```

You should see:
- Header comment with export metadata
- Constraint creation statements
- Batched node MERGE statements

### 4. Import into Neo4j (Manual)

```bash
# Set connection details
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# Import via cypher-shell
cat exports/neo4j/graph.cypher | cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD
```

---

## Quick Start: Sync

### 1. Set Environment Variables

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
```

**Security Note**: Never commit credentials to version control. Use a `.env` file (gitignored) or system environment configuration.

### 2. Dry-Run First (Recommended)

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
```

**Output**:
```json
{
  "mode": "dry-run",
  "profile": "default",
  "target_uri": "bolt://localhost:7687",
  "nodes_processed": 42,
  "relationships_processed": 87,
  "nodes_created": 0,
  "nodes_updated": 0,
  "relationships_created": 0,
  "relationships_updated": 0,
  "skipped_count": 0,
  "failed_count": 0,
  "duration_seconds": 0.156
}
```

This validates connection and data without mutating the database.

### 3. Execute Live Sync

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

**First Run Output**:
```json
{
  "mode": "sync",
  "profile": "default",
  "target_uri": "bolt://localhost:7687",
  "nodes_processed": 42,
  "relationships_processed": 87,
  "nodes_created": 42,
  "nodes_updated": 0,
  "relationships_created": 87,
  "relationships_updated": 0,
  "skipped_count": 0,
  "failed_count": 0,
  "duration_seconds": 1.234
}
```

### 4. Re-sync (Idempotent)

Run the same command again:

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

**Second Run Output**:
```json
{
  "mode": "sync",
  "nodes_processed": 42,
  "relationships_processed": 87,
  "nodes_created": 0,
  "nodes_updated": 42,
  "relationships_created": 0,
  "relationships_updated": 87,
  "skipped_count": 0,
  "failed_count": 0,
  "duration_seconds": 1.189
}
```

Notice `nodes_created` and `relationships_created` are now zero; all records were updated instead.

---

## Exploring Your Graph in Neo4j

### Using Neo4j Browser

1. Open Neo4j Browser: `http://localhost:7474`
2. Connect with your credentials
3. Run exploratory queries

#### View All Node Labels

```cypher
CALL db.labels()
YIELD label
RETURN label
ORDER BY label;
```

#### Count Nodes by Type

```cypher
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC;
```

#### Sample Nodes

```cypher
MATCH (n:AuditgraphNote)
RETURN n
LIMIT 10;
```

#### Explore Relationships

```cypher
MATCH (a)-[r:RELATES_TO]->(b)
RETURN a.name AS from, r.type AS relationship, b.name AS to
LIMIT 20;
```

#### Visualize a Subgraph

```cypher
MATCH path = (a:AuditgraphNote)-[r:RELATES_TO*1..2]-(b)
RETURN path
LIMIT 50;
```

---

## Common Scenarios

### Scenario 1: Regular Sync Workflow

```bash
# Daily workflow: ingest changes, sync to Neo4j
cd auditgraph
source .venv/bin/activate

# Update graph from new/changed files
auditgraph ingest --root . --config config/pkg.yaml
auditgraph extract --root .
auditgraph link --root .
auditgraph index --root .

# Sync to Neo4j
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

### Scenario 2: Export for Sharing

```bash
# Generate a portable Cypher export for team member
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/shared-graph.cypher

# Share file via email, Slack, etc.
# Recipient imports into their own Neo4j instance
```

### Scenario 3: Multiple Profiles

```bash
# Export from "work" profile
auditgraph export-neo4j --root . --config config/pkg-work.yaml --output exports/neo4j/work-graph.cypher

# Sync "personal" profile to different Neo4j database
export NEO4J_DATABASE="personal"
auditgraph sync-neo4j --root . --config config/pkg-personal.yaml
```

### Scenario 4: CI/CD Integration

```yaml
# .github/workflows/sync-neo4j.yml
name: Sync to Neo4j
on:
  push:
    branches: [main]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e . && pip install neo4j
      - run: auditgraph rebuild --root . --config config/pkg.yaml
      - run: auditgraph sync-neo4j --root . --config config/pkg.yaml
        env:
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
```

---

## Troubleshooting

### Error: "Missing environment variable: NEO4J_URI"

**Cause**: Sync operation requires connection settings via environment variables.

**Fix**:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
```

Or create a `.env` file and source it:
```bash
# .env (add to .gitignore!)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# Load it
source .env
```

---

### Error: "Connection refused" or "ServiceUnavailable"

**Cause**: Neo4j instance not running or unreachable.

**Fix**:
1. Verify Neo4j is running: `neo4j status` (or check Docker container)
2. Verify connection URI matches your Neo4j configuration
3. Check firewall rules if connecting remotely

**Test connection**:
```bash
cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD "RETURN 1 AS test;"
```

---

### Error: "AuthError: Authentication failed"

**Cause**: Incorrect username or password.

**Fix**:
1. Verify credentials with cypher-shell test (above)
2. Reset Neo4j password if needed: `neo4j-admin set-initial-password <new_password>`
3. Update `NEO4J_PASSWORD` environment variable

---

### Error: "Node with missing from_id or to_id"

**Cause**: Link references entity that doesn't exist (data inconsistency).

**Fix**:
This is a warning, not a fatal error. The relationship is skipped and counted in `skipped_count`.

**Investigate**:
```bash
# Check extraction logs
auditgraph extract --root . --config config/pkg.yaml

# Rebuild if needed
auditgraph rebuild --root . --config config/pkg.yaml
```

---

### Performance: Sync is slow for large datasets

**Cause**: Default batch size or connection pool may not be optimal for your setup.

**Fix**:
1. Ensure Neo4j has sufficient resources (memory, CPU)
2. Use dedicated Neo4j instance (not shared development instance)
3. Monitor Neo4j metrics during sync
4. Future enhancement: Configurable batch size

**Workaround**: Export to file and import offline (faster for very large datasets):
```bash
auditgraph export-neo4j --output graph.cypher
time cat graph.cypher | cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD
```

---

## Next Steps

- **Query Design**: Learn Cypher patterns for your specific exploration workflows
- **Visualization Tools**: Explore Neo4j Bloom, Arrows.app, or custom D3.js views
- **Graph Algorithms**: Use Neo4j Graph Data Science library for centrality, communities, etc.
- **Integration**: Build custom dashboards or reports querying Neo4j directly

## Additional Resources

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Python Driver Documentation](https://neo4j.com/docs/python-manual/current/)
- [Neo4j Browser Guide](https://neo4j.com/developer/neo4j-browser/)
- [Auditgraph Main Documentation](../../../README.md)
