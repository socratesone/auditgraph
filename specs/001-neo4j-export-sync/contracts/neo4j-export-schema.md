# Neo4j Export Schema Contract

**Feature**: Neo4j Export and Sync  
**Created**: 2026-02-17  
**Version**: 1.0.0

## Overview

This document defines the Cypher schema, property conventions, and example statements for Neo4j export/sync operations.

## Label Conventions

All auditgraph entities are mapped to Neo4j labels with the `Auditgraph` prefix to provide namespace isolation.

**Mapping Rule**: `type="<entity_type>"` in auditgraph → `:Auditgraph<EntityType>` label in Neo4j

**Examples**:
- `type="note"` →  `:AuditgraphNote`
- `type="task"` → `:AuditgraphTask`
- `type="decision"` → `:AuditgraphDecision`
- `type="event"` → `:AuditgraphEvent`
- `type="entity"` → `:AuditgraphEntity` (generic fallback)

## Node Schema

### Required Properties

All nodes MUST include:

**Property** | **Type** | **Description**
--- | --- | ---
`id` | string | Stable auditgraph entity identifier (unique constraint enforced)
`type` | string | Original auditgraph entity type
`name` | string | Human-readable entity name

### Optional Properties

**Property** | **Type** | **Description**
--- | --- | ---
`canonical_key` | string | Auditgraph canonical key for deduplication
`profile` | string | Source auditgraph profile name
`run_id` | string | Last extraction run identifier
`source_path` | string | Original source file path
`source_hash` | string | Content hash of source file

### Example Node

```cypher
MERGE (:AuditgraphNote {
  id: "entity_20240217_abc123",
  type: "note",
  name: "Meeting Notes: Q1 Planning",
  canonical_key: "note:meeting-notes-q1-planning",
  profile: "default",
  run_id: "run_20240217_xyz789",
  source_path: "notes/2024/q1-planning.md",
  source_hash: "sha256:def456..."
})
```

## Relationship Schema

### Required Properties

All relationships MUST include:

**Property** | **Type** | **Description**
--- | --- | ---
`id` | string | Stable auditgraph link identifier (unique constraint enforced)
`type` | string | Relationship type from auditgraph linking rules
`rule_id` | string | Auditgraph rule that created this relationship

### Optional Properties

**Property** | **Type** | **Description**
--- | --- | ---
`confidence` | float | Confidence score (0.0-1.0)
`authority` | string | Authority level (`authoritative` or `suggested`)
`evidence` | string (JSON) | Serialized array of evidence references

### Relationship Types

Auditgraph uses typed relationships stored in the `type` property. The Neo4j relationship label is always `:RELATES_TO` (generic), with specific semantics captured in the `type` property.

**Common Types**:
- `relates_to`: Generic co-occurrence relationship
- `mentions`: One entity mentions another
- `depends_on`: Dependency relationship
- `implements`: Implementation relationship
- `caused_by`: Causal relationship
- `decided_in`: Decision relationship

### Example Relationship

```cypher
MATCH (a:AuditgraphNote {id: "entity_abc123"})
MATCH (b:AuditgraphTask {id: "entity_def456"})
MERGE (a)-[:RELATES_TO {
  id: "lnk_20240217_ghi789",
  type: "mentions",
  rule_id: "link.source_cooccurrence.v1",
  confidence: 1.0,
  authority: "authoritative",
  evidence: "[{\"source_path\": \"notes/2024/q1-planning.md\", \"source_hash\": \"sha256:xyz...\"}]"
}]->(b)
```

## Constraint Declarations

Unique constraints are required for idempotent MERGE operations.

### Node Constraints

One constraint per label, enforcing uniqueness on the `id` property:

```cypher
CREATE CONSTRAINT auditgraph_note_id_unique IF NOT EXISTS
FOR (n:AuditgraphNote) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT auditgraph_task_id_unique IF NOT EXISTS
FOR (n:AuditgraphTask) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT auditgraph_decision_id_unique IF NOT EXISTS
FOR (n:AuditgraphDecision) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT auditgraph_event_id_unique IF NOT EXISTS
FOR (n:AuditgraphEvent) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT auditgraph_entity_id_unique IF NOT EXISTS
FOR (n:AuditgraphEntity) REQUIRE n.id IS UNIQUE;
```

### Relationship Constraints

(Optional, for Neo4j Enterprise Edition only):

```cypher
CREATE CONSTRAINT auditgraph_relationship_id_unique IF NOT EXISTS
FOR ()-[r:RELATES_TO]-() REQUIRE r.id IS UNIQUE;
```

**Note**: Relationship uniqueness constraints are only supported in Neo4j Enterprise Edition (4.4+). Community Edition export/sync operations will skip relationship constraints and rely on application-level deduplication via MERGE with id matching.

## Export File Format

### File Structure

```
// Neo4j Export from Auditgraph
// Profile: <profile_name>
// Timestamp: <iso8601_timestamp>
// Nodes: <node_count>
// Relationships: <relationship_count>
// Format Version: 1.0.0

// === Constraints ===
<constraint statements>

// === Nodes (Batch 1 of N) ===
:begin
<node MERGE statements 1-1000>
:commit

// === Nodes (Batch 2 of N) ===
:begin
<node MERGE statements 1001-2000>
:commit

// ... (continue for all nodes)

// === Relationships (Batch 1 of M) ===
:begin
<relationship MERGE statements 1-1000>
:commit

// === Relationships (Batch 2 of M) ===
:begin
<relationship MERGE statements 1001-2000>
:commit

// ... (continue for all relationships)
```

### Batch Transaction Syntax

Neo4j shell syntax (`:begin` / `:commit`) for use with `cypher-shell`:

```cypher
:begin
MERGE (n:AuditgraphNote {id: $id_1}) SET n.name = $name_1, n.type = $type_1;
MERGE (n:AuditgraphNote {id: $id_2}) SET n.name = $name_2, n.type = $type_2;
// ... (up to 1000 statements)
:commit
```

**Alternative Syntax** (explicit ACID, compatible with Neo4j Browser):

```cypher
BEGIN;
MERGE (n:AuditgraphNote {id: "entity_abc"}) SET n.name = "Example", n.type = "note";
MERGE (n:AuditgraphNote {id: "entity_def"}) SET n.name = "Another", n.type = "note";
COMMIT;
```

## MERGE Statement Patterns

### Node MERGE (Idempotent Create/Update)

```cypher
MERGE (n:AuditgraphNote {id: "entity_20240217_abc123"})
SET n.name = "Meeting Notes: Q1 Planning",
    n.type = "note",
    n.canonical_key = "note:meeting-notes-q1-planning",
    n.profile = "default",
    n.run_id = "run_20240217_xyz789",
    n.source_path = "notes/2024/q1-planning.md",
    n.source_hash = "sha256:def456..."
```

**Behavior**:
- If node with `id="entity_20240217_abc123"` exists: Update all SET properties
- If node does not exist: Create with `:AuditgraphNote` label and all properties
- Requires unique constraint on `id` for optimal performance

### Relationship MERGE (Idempotent Create/Update)

```cypher
MATCH (a {id: "entity_abc123"}), (b {id: "entity_def456"})
MERGE (a)-[r:RELATES_TO {id: "lnk_20240217_ghi789"}]->(b)
SET r.type = "mentions",
    r.rule_id = "link.source_cooccurrence.v1",
    r.confidence = 1.0,
    r.authority = "authoritative",
    r.evidence = "[{\"source_path\": \"notes/2024/q1-planning.md\"}]"
```

**Behavior**:
- If both nodes exist AND relationship with `id="lnk_20240217_ghi789"` exists: Update SET properties
- If both nodes exist AND relationship does not exist: Create with all properties
- If either node missing: MATCH fails, skip relationship (logged in skipped_count)

**Alternative Pattern** (more explicit, slightly slower):

```cypher
MATCH (a:AuditgraphNote {id: "entity_abc123"})
MATCH (b:AuditgraphTask {id: "entity_def456"})
MERGE (a)-[r:RELATES_TO {id: "lnk_ghi789"}]->(b)
ON CREATE SET r.type = "mentions", r.rule_id = "link.source_cooccurrence.v1"
ON MATCH SET r.type = "mentions", r.rule_id = "link.source_cooccurrence.v1"
```

## Example Complete Export (Minimal)

```cypher
// Neo4j Export from Auditgraph
// Profile: default
// Timestamp: 2024-02-17T15:30:00Z
// Nodes: 2
// Relationships: 1
// Format Version: 1.0.0

// === Constraints ===
CREATE CONSTRAINT auditgraph_note_id_unique IF NOT EXISTS
FOR (n:AuditgraphNote) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT auditgraph_task_id_unique IF NOT EXISTS
FOR (n:AuditgraphTask) REQUIRE n.id IS UNIQUE;

// === Nodes (Batch 1 of 1) ===
:begin
MERGE (n:AuditgraphNote {id: "entity_001"})
SET n.name = "Project Overview", n.type = "note", n.profile = "default";

MERGE (n:AuditgraphTask {id: "entity_002"})
SET n.name = "Implement Feature X", n.type = "task", n.profile = "default";
:commit

// === Relationships (Batch 1 of 1) ===
:begin
MATCH (a {id: "entity_001"}), (b {id: "entity_002"})
MERGE (a)-[r:RELATES_TO {id: "lnk_001"}]->(b)
SET r.type = "mentions", r.rule_id = "link.source_cooccurrence.v1";
:commit
```

## Import Instructions

### Using cypher-shell

```bash
# Set environment variables
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

# Import via pipe
cat export.cypher | cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD

# Or using file argument
cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD -f export.cypher
```

### Using Neo4j Browser

1. Open Neo4j Browser at `http://localhost:7474`
2. Connect with credentials
3. Copy/paste export file contents into query editor
4. Execute (may need to execute in sections if file is very large)

### Verification Queries

After import, verify data:

```cypher
// Count nodes by label
MATCH (n)
RETURN labels(n) AS label, count(n) AS count
ORDER BY count DESC;

// Count relationships by type property
MATCH ()-[r]->()
RETURN r.type AS relationship_type, count(r) AS count
ORDER BY count DESC;

// Sample nodes
MATCH (n)
RETURN n
LIMIT 10;

// Sample relationships with connected nodes
MATCH (a)-[r]->(b)
RETURN a.name, r.type, b.name
LIMIT 10;
```

## Compatibility Notes

- **Neo4j Version**: Tested with Neo4j 4.4+ and 5.x
- **Cypher Shell**: Compatible with versions bundled with Neo4j 4.0+
- **IF NOT EXISTS**: Requires Neo4j 4.4+; for older versions, constraint creation may fail on re-execution (expected, safe to ignore)
- **Relationship Constraints**: Enterprise Edition only (4.4+); Community Edition skips

## Redaction Notes

All node and relationship properties pass through the auditgraph redaction policy before export/sync. Sensitive fields (credentials, tokens, PEM keys) are replaced with `[REDACTED]` marker.

Example redacted node:

```cypher
MERGE (n:AuditgraphNote {id: "entity_abc"})
SET n.name = "API Configuration",
    n.api_key = "[REDACTED]",
    n.source_path = "config/api.md"
```

The redaction policy is profile-specific and configured in `config/pkg.yaml`.
