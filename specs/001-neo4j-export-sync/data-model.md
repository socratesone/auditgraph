# Data Model: Neo4j Export and Sync

**Feature**: Neo4j Export and Sync  
**Created**: 2026-02-17  
**Status**: Design Complete

## Overview

This document defines the data structures and transformations for exporting auditgraph knowledge graphs to Neo4j-compatible formats and syncing them to live Neo4j instances.

## Core Entities

### GraphNodeRecord

Represents an auditgraph entity prepared for Neo4j export/sync.

**Source**: Loaded from `.pkg/profiles/<profile>/entities/<shard>/<entity_id>.json`

**Fields**:
- `id` (string, required): Stable auditgraph entity identifier (e.g., `entity_abc123`)
- `type` (string, required): Entity type from auditgraph knowledge model (e.g., `note`, `task`, `decision`)
- `neo4j_label` (string, derived): Neo4j label with `Auditgraph` prefix (e.g., `:AuditgraphNote`)
- `name` (string, required): Human-readable entity name
- `canonical_key` (string, optional): Auditgraph canonical key for deduplication
- `profile` (string, required): Source profile name
- `run_id` (string, optional): Last extraction run identifier
- `source_path` (string, optional): Original source file path
- `source_hash` (string, optional): Source file content hash

**Transformations**:
1. Load entity JSON from file
2. Apply redaction policy to all fields
3. Map `type` → `neo4j_label` using prefix convention (`type="note"` becomes `neo4j_label=":AuditgraphNote"`)
4. Extract provenance metadata (profile, run_id, source references)
5. Sort by `id` for deterministic ordering

**Validation Rules**:
- `id` must be non-empty and unique within export scope
- `type` must be valid auditgraph entity type
- `name` must be non-empty after redaction

---

### GraphRelationshipRecord

Represents a typed link between two GraphNodeRecords.

**Source**: Loaded from `.pkg/profiles/<profile>/links/<shard>/<link_id>.json`

**Fields**:
- `id` (string, required): Stable auditgraph link identifier (e.g., `lnk_xyz789`)
- `from_id` (string, required): Source node `id` (foreign key to GraphNodeRecord)
- `to_id` (string, required): Target node `id` (foreign key to GraphNodeRecord)
- `type` (string, required): Relationship type (e.g., `relates_to`, `mentions`, `depends_on`)
- `rule_id` (string, required): Auditgraph linking rule that created this relationship
- `confidence` (float, optional): Confidence score (0.0-1.0)
- `authority` (string, optional): Authority level (`authoritative`, `suggested`)
- `evidence` (array of objects, optional): Evidence references with source_path and source_hash

**Transformations**:
1. Load link JSON from file
2. Apply redaction policy to evidence references
3. Verify `from_id` and `to_id` exist in node set (skip relationship if missing)
4. Sort by (`from_id`, `to_id`, `id`) for deterministic ordering

**Validation Rules**:
- `id` must be non-empty and unique within export scope
- `from_id` and `to_id` must reference existing GraphNodeRecords
- `type` must be non-empty
- If present, `confidence` must be in range [0.0, 1.0]

---

### ExportSummary

Represents the outcome of one export or sync operation.

**Fields**:
- `mode` (string, required): Operation mode (`export`, `sync`, `dry-run`)
- `profile` (string, required): Source profile name
- `timestamp` (string, required): ISO 8601 timestamp of operation start
- `output_path` (string, required for export): Absolute path to generated `.cypher` file
- `target_uri` (string, required for sync): Neo4j connection URI (credentials redacted)
- `nodes_processed` (int, required): Count of GraphNodeRecords processed
- `relationships_processed` (int, required): Count of GraphRelationshipRecords processed
- `nodes_created` (int, sync only): Count of nodes created in target database
- `nodes_updated` (int, sync only): Count of nodes updated in target database
- `relationships_created` (int, sync only): Count of relationships created
- `relationships_updated` (int, sync only): Count of relationships updated
- `skipped_count` (int, required): Count of invalid/missing records skipped
- `failed_count` (int, required): Count of records that failed processing
- `errors` (array of objects, optional): Error details with message and affected record IDs
- `duration_seconds` (float, required): Total operation duration

**Validation Rules**:
- `mode` must be one of: `export`, `sync`, `dry-run`
- All count fields must be non-negative integers
- `duration_seconds` must be non-negative
- In `dry-run` mode, `*_created` and `*_updated` counts should be zero

---

### Neo4jConnectionProfile

Represents connection settings for sync operations.

**Source**: Environment variables

**Fields**:
- `uri` (string, required): Neo4j connection URI (e.g., `bolt://localhost:7687`, `neo4j://remote:7687`)
- `user` (string, required): Authentication username
- `password` (string, required): Authentication password (never logged or exported)
- `database` (string, optional): Target database name (defaults to `neo4j`)
- `max_connection_pool_size` (int, optional): Driver connection pool size (defaults to 50)

**Source Environment Variables**:
- `NEO4J_URI` → `uri`
- `NEO4J_USER` → `user`
- `NEO4J_PASSWORD` → `password`
- `NEO4J_DATABASE` → `database` (optional)

**Validation Rules**:
- `uri` must start with `bolt://`, `neo4j://`, `bolt+s://`, or `neo4j+s://`
- `user` must be non-empty
- `password` must be non-empty
- If provided, `max_connection_pool_size` must be > 0

---

## Data Flow

### Export Flow

```
1. Load Configuration
   - Read active profile from pkg.yaml
   - Build redactor from profile security settings

2. Discover Graph Records
   - Scan .pkg/profiles/<profile>/entities/ directory
   - Load all entity JSON files → GraphNodeRecords
   - Scan .pkg/profiles/<profile>/links/ directory
   - Load all link JSON files → GraphRelationshipRecords

3. Apply Transformations
   - Redact all node and relationship fields
   - Map entity types to Neo4j labels
   - Filter relationships with missing nodes → skipped_count
   - Sort nodes by id
   - Sort relationships by (from_id, to_id, id)

4. Generate Cypher File
   - Write header comment with export metadata
   - Write constraint creation statements
   - Batch nodes into groups of 1000
   - For each batch: BEGIN transaction, MERGE statements, COMMIT
   - Batch relationships into groups of 1000
   - For each batch: BEGIN transaction, MATCH + MERGE statements, COMMIT

5. Return ExportSummary
   - Record counts, output path, duration
```

### Sync Flow

```
1. Load Configuration
   - Read active profile from pkg.yaml
   - Build redactor from profile security settings
   - Load Neo4jConnectionProfile from environment variables

2. Establish Connection
   - Create Neo4j driver with connection profile settings
   - Execute pre-flight ping query to verify connectivity
   - If dry-run mode: skip connection (or connect but don't commit)

3. Discover Graph Records
   - Same as Export Flow steps 2-3

4. Ensure Constraints
   - Generate constraint creation Cypher for each label
   - Execute constraint statements (idempotent IF NOT EXISTS)
   - Handle admin permission errors with clear diagnostic

5. Sync Nodes
   - Batch nodes into groups of 1000
   - For each batch:
     - Open write transaction
     - Execute parameterized MERGE for each node
     - Track created vs updated counts
     - COMMIT transaction (skip if dry-run)

6. Sync Relationships
   - Batch relationships into groups of 1000
   - For each batch:
     - Open write transaction
     - Execute parameterized MATCH + MERGE for each relationship
     - Track created vs updated counts
     - COMMIT transaction (skip if dry-run)

7. Return ExportSummary
   - Record counts, target URI, duration, errors
```

---

## Deterministic Ordering Rules

To ensure reproducible exports (FR-011), all records are sorted before processing:

**Nodes**: Sort by `id` (lexicographic ascending)

**Relationships**: Sort by tuple `(from_id, to_id, id)` (lexicographic ascending at each level)

**Cypher Statement Order**:
1. Constraint creation statements (sorted by label name)
2. Node MERGE statements (in node sort order)
3. Relationship MERGE statements (in relationship sort order)

This guarantees identical output for identical inputs across runs and platforms.

---

## Error Handling

### Skipped Records

Records are skipped (incrementing `skipped_count`) when:
- Entity JSON file is malformed or missing required fields
- Link references `from_id` or `to_id` not found in node set
- Redaction results in invalid data (e.g., empty name after redaction)

Skipped records are logged but do not fail the operation.

### Failed Records

Records fail (incrementing `failed_count` and populating `errors` array) when:
- Cypher generation raises exception during serialization
- Neo4j transaction fails with `ClientError` (syntax, constraint violation)
- Neo4j transaction fails with non-transient error

Failed records abort the current batch transaction and continue with next batch.

### Fatal Errors

Operation aborts immediately (before processing any records) when:
- Required environment variables missing (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- Connection to Neo4j fails (ServiceUnavailable, AuthError)
- Profile directory or entity/link directories missing
- Insufficient permissions to write export file

---

## Performance Considerations

### Memory Usage

- Records loaded incrementally during iteration (not all in memory)
- Batch processing limits in-flight transaction size to 1000 records
- Neo4j driver pools connections (default 50, configurable)

### Latency

- Export: Dominated by file I/O and Cypher string building (~100K records in <2 minutes target)
- Sync: Dominated by network RTT and Neo4j transaction commit (~100K records in <2 minutes target)
- Constraint creation: One-time overhead at sync start (~100ms per constraint)

### Scalability

- Tested target: 100K nodes + 300K relationships = 400K total records
- Projected max: 1M total records within acceptable latency (linear scaling expected)

---

## Schema Evolution

Future-proofing considerations:

- Labels are derived from entity type; new types automatically get new labels
- Properties are open-ended; new entity/link fields automatically included
- Constraint names include label to avoid collisions
- Export file header includes format version for compatibility tracking

**Current Format Version**: `1.0.0`
