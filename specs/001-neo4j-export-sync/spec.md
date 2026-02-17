# Feature Specification: Neo4j Export and Sync

**Feature Branch**: `001-neo4j-export-sync`  
**Created**: 2026-02-17  
**Status**: Draft  
**Input**: User description: "Create a neo4j export/sync feature for auditgraph so graph artifacts can be explored in Neo4j graph explorer tools"

## Clarifications

### Session 2026-02-17

- Q: What export format should the feature produce? → A: Cypher MERGE statements (.cypher file with batched transactions)
- Q: Where should Neo4j connection settings be stored? → A: Environment variables (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
- Q: What batch size should be used when exporting/syncing large graphs? → A: 1000 records per batch (balanced approach)
- Q: How should auditgraph entity types map to Neo4j node labels? → A: Direct mapping with prefix (type "note" becomes label `:AuditgraphNote`)
- Q: How should sync achieve idempotency when creating/updating nodes and relationships? → A: MERGE on stable ID (create if missing, update if exists, requires unique constraint)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export graph for external exploration (Priority: P1)

As an engineer, I can produce a complete graph export in a Neo4j-ingestible format from the current auditgraph profile so I can load it into my graph explorer workflow.

**Why this priority**: This is the minimum valuable outcome because it enables immediate visualization and exploration without changing existing storage behavior.

**Independent Test**: Can be fully tested by running the Neo4j export command on an existing workspace and verifying that output artifacts include all exported nodes and relationships with stable identifiers.

**Acceptance Scenarios**:

1. **Given** a workspace with extracted entities and links, **When** the user runs Neo4j export, **Then** the system produces deterministic export artifacts containing nodes and relationships for the active profile.
2. **Given** two repeated exports with unchanged inputs and configuration, **When** the user compares outputs, **Then** the exported data content is identical apart from explicitly documented runtime metadata.

---

### User Story 2 - Sync graph into a Neo4j instance (Priority: P2)

As an engineer, I can sync the current auditgraph graph into a reachable Neo4j database so I can query and browse the graph directly in Neo4j tools.

**Why this priority**: Direct sync removes manual import friction and keeps an external graph explorer in step with auditgraph runs.

**Independent Test**: Can be tested by running sync against a reachable target database and confirming that expected nodes and relationships are present and updated idempotently.

**Acceptance Scenarios**:

1. **Given** a reachable target database and valid connection settings, **When** the user runs sync, **Then** all eligible graph records are created or updated in the target database.
2. **Given** a previously synced dataset, **When** the user runs sync again without input changes, **Then** the resulting graph content remains unchanged and no duplicate records are introduced.

---

### User Story 3 - Safe and observable operations (Priority: P3)

As an engineer, I can run export/sync with clear summaries, failure signals, and dry-run behavior so I can trust outcomes before applying changes.

**Why this priority**: Safety and observability reduce operational risk when connecting local knowledge artifacts to external systems.

**Independent Test**: Can be tested by running dry-run and failure cases and verifying that no target mutations occur during dry-run and that actionable error details are returned.

**Acceptance Scenarios**:

1. **Given** dry-run mode is enabled, **When** the user runs sync, **Then** the system reports planned create/update counts without mutating the target database.
2. **Given** invalid or unreachable connection settings, **When** the user runs sync, **Then** the system fails with a clear error message and preserves local artifacts.

### Edge Cases

- Workspace contains entities but no links; export/sync still succeeds and reports zero relationships.
- Link references a missing node artifact; operation skips invalid relationship and reports skipped count.
- Target database already contains unrelated data; operation only touches records in the auditgraph namespace.
- Large graph volumes; operation processes records in batches of 1000, commits each batch as a transaction, and reports partial progress if interrupted.
- Redaction-sensitive fields are present; exported/synced values follow existing redaction policy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a user-invoked capability to generate Neo4j-ingestible graph exports from the active profile as Cypher MERGE statements in a `.cypher` file with batched transactions.
- **FR-002**: Export MUST include entity nodes and link relationships using existing stable auditgraph identifiers as canonical keys.
- **FR-003**: System MUST include enough exported properties for graph exploration, including node type mapped to Neo4j label with "Auditgraph" prefix (e.g., entity type "note" becomes `:AuditgraphNote`), node name, relationship type, and provenance identifiers when available.
- **FR-004**: System MUST provide a user-invoked capability to sync graph data into a target Neo4j database using connection settings from environment variables (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).
- **FR-005**: Sync MUST be idempotent for unchanged inputs using Neo4j MERGE operations keyed on auditgraph stable identifiers, creating nodes and relationships on first sync and updating properties on subsequent syncs to avoid duplicates.
- **FR-006**: Sync MUST support a dry-run mode that reports intended changes without mutating the target database.
- **FR-007**: System MUST produce an operation summary for export and sync including counts of processed, created, updated, skipped, and failed records.
- **FR-008**: System MUST enforce existing profile isolation so only data from the active profile is exported or synced.
- **FR-009**: System MUST apply existing redaction policy to exported and synced fields that are classified as sensitive.
- **FR-010**: System MUST fail safely with actionable diagnostics when required environment variables are missing, connection settings are invalid, credentials are incorrect, or target database is unreachable.
- **FR-011**: System MUST define deterministic ordering rules for exported records to preserve reproducibility across repeated runs.
- **FR-012**: System MUST preserve current file-based artifacts as the authoritative audit record for pipeline determinism and replayability.
- **FR-013**: System MUST process export and sync operations in batches of 1000 records, committing each batch as a separate transaction to balance memory usage and transaction overhead.
- **FR-014**: Sync operation MUST create or verify unique constraints on auditgraph stable identifier properties in the target database before performing MERGE operations to ensure idempotency.

### Key Entities *(include if feature involves data)*

- **Graph Node Record**: Represents an auditgraph entity prepared for export/sync; includes stable id, type (mapped to Neo4j label with "Auditgraph" prefix), name, and profile/run provenance attributes.
- **Graph Relationship Record**: Represents a typed link between two node records; includes stable relationship id, source node id, target node id, relationship type, and evidence/provenance attributes.
- **Sync Operation Summary**: Represents one export or sync execution outcome; includes mode (export/sync/dry-run), scope, timestamps, counts, and error details.
- **Neo4j Connection Profile**: Represents user-provided target connection settings and namespace scope used during sync.

### Assumptions

- Teams using this feature have an accessible Neo4j environment managed outside auditgraph.
- Existing auditgraph extraction and linking stages continue to define source graph content.
- Users primarily need external visualization and exploratory querying, not a full replacement of auditgraph storage internals.

### Dependencies

- A populated auditgraph profile containing entity and link artifacts.
- Network connectivity and authorization to access the target Neo4j instance.
- Clear namespace conventions to prevent collisions with unrelated records in shared target databases.
- Target database permissions to create unique constraints on node and relationship properties for idempotent MERGE operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of successful export runs complete within 2 minutes for datasets up to 100,000 nodes and 300,000 relationships.
- **SC-002**: Repeated export runs with unchanged inputs produce identical node and relationship record sets in 100% of validation comparisons.
- **SC-003**: At least 99% of sync runs with valid connectivity complete without manual intervention, measured over a minimum of 200 sync runs across a 14-day validation window.
- **SC-004**: In user validation sessions with at least 10 participants following a scripted task, at least 90% can locate a known entity and inspect one-hop relationships in their graph explorer within 3 minutes of sync.
- **SC-005**: In regression checks, duplicate node or relationship creation rate remains 0% across repeated syncs of unchanged inputs.
