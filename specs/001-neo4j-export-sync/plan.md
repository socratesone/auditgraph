# Implementation Plan: Neo4j Export and Sync

**Branch**: `001-neo4j-export-sync` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-neo4j-export-sync/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable engineers to export auditgraph knowledge graphs to Neo4j-compatible Cypher format and sync directly into running Neo4j instances. Export generates deterministic `.cypher` files with batched MERGE statements. Sync uses environment-variable-configured connections with idempotent MERGE operations for real-time graph exploration workflows.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: neo4j-driver (official Neo4j Python driver), pyyaml (existing), pytest (existing)  
**Storage**: File-based artifacts remain authoritative; Neo4j as optional projection target  
**Testing**: pytest with fixtures for Neo4j test containers or mocked driver  
**Target Platform**: Linux/macOS/Windows CLI  
**Project Type**: Single project (CLI-first with export/sync modules)  
**Performance Goals**: Export 100K nodes + 300K relationships in <2 minutes; sync idempotency overhead <10%  
**Constraints**: Deterministic export ordering; zero duplicate creation on repeated sync; environment-only credentials  
**Scale/Scope**: Target datasets up to 1M total records; batch size 1000 records/transaction

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Justification |
|------|--------|---------------|
| **DRY**: No duplication of export/sync logic | ✅ PASS | Export and sync share common graph traversal; extraction logic reused from existing loaders |
| **SRP**: Export module has one reason to change | ✅ PASS | Export handles file generation only; sync handles database communication only; both delegate to shared graph serializers |
| **OCP**: Extendable to other graph formats | ✅ PASS | Graph record abstraction decouples from Cypher generation; future formats (GraphML, JSON-LD) can implement same interface |
| **LSP**: Neo4j driver abstraction substitutable | ✅ PASS | Driver interface allows test doubles and alternative Neo4j client implementations |
| **ISP**: Focused interfaces for export vs sync | ✅ PASS | Export operation interface separate from sync operation interface; clients depend only on needed contract |
| **DIP**: Core logic independent of Neo4j driver | ✅ PASS | Graph record builders are pure functions; Neo4j driver is injected dependency |
| **TDD**: All behavior test-first | ✅ PASS | Export determinism, sync idempotency, batch behavior, error handling all have failing tests before implementation |
| **Simplicity**: Minimal viable implementation | ✅ PASS | No speculative abstractions; single export format; single sync strategy; environment-only config |

**Result**: All gates pass. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-neo4j-export-sync/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (generated in this feature directory)
├── data-model.md        # Phase 1 output (generated in this feature directory)
├── quickstart.md        # Phase 1 output (generated in this feature directory)
├── contracts/           # Phase 1 output (generated in this feature directory)
│   └── neo4j-export-schema.md
├── checklists/          # Quality gates
│   └── requirements.md  # Specification validation (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
auditgraph/
├── neo4j/                    # NEW: Neo4j export/sync module
│   ├── __init__.py
│   ├── export.py             # Cypher file generation
│   ├── sync.py               # Live database sync
│   ├── records.py            # Graph record abstraction
│   ├── cypher_builder.py     # Cypher statement generator
│   └── connection.py         # Neo4j driver wrapper
├── cli.py                    # UPDATED: Add export-neo4j, sync-neo4j commands
├── storage/
│   └── loaders.py            # REUSED: Entity/link loading
└── utils/
    └── redaction.py          # REUSED: Redaction policy

tests/
├── test_neo4j_export.py              # NEW: Export determinism, ordering
├── test_neo4j_sync.py                # NEW: Sync idempotency, batching
├── test_neo4j_records.py             # NEW: Graph record serialization
├── test_neo4j_cypher_builder.py      # NEW: Cypher statement generation
├── test_neo4j_connection.py          # NEW: Connection handling, error cases
└── fixtures/
    └── neo4j_fixtures.py             # NEW: Test graph data, mock driver

config/
└── pkg.yaml                  # UNCHANGED: Environment variable config documented in quickstart

exports/
└── neo4j/                    # NEW: Default export output directory
```

**Structure Decision**: Single project layout chosen (auditgraph is a CLI-first tool). New `auditgraph/neo4j/` module added alongside existing pipeline modules (`ingest/`, `extract/`, `link/`, `index/`, `query/`, `export/`). Test structure mirrors source with `test_neo4j_*` naming convention matching existing spec/user-story tests.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations detected. All constitution gates pass.*

---

# Phase 0: Research & Discovery

## Research Tasks

### R1: Neo4j Python Driver Best Practices

**Question**: What are the recommended patterns for batched writes, connection pooling, and transaction management with the official neo4j-driver?

**Findings**:
- Official driver: `neo4j` package from PyPI
- Recommended pattern: Use `driver.session()` context managers for automatic resource cleanup
- Batch writes: Use `session.write_transaction()` with parameterized Cypher queries
- Connection pooling: Driver manages pool internally; configure via `max_connection_pool_size`
- Transaction batching: Group 1000 records per transaction balances memory and commit overhead
- Environment variables: Standard pattern is `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

**Decision**: Use official `neo4j` driver with write transactions for idempotent MERGE operations. Configure pool size to 50 (driver default) for sync operations.

**Alternatives Considered**:
- py2neo (community driver) - rejected: less actively maintained, different API surface
- Direct Bolt protocol implementation - rejected: unnecessary complexity, driver handles connection management

---

### R2: Cypher MERGE Idempotency and Constraints

**Question**: How do we ensure MERGE operations are truly idempotent and what constraints are required?

**Findings**:
- MERGE creates node/relationship if missing, matches if exists based on specified properties
- Requires unique constraint on merge key property for best performance and correctness
- Syntax: `CREATE CONSTRAINT entity_id_unique FOR (n:AuditgraphEntity) REQUIRE n.id IS UNIQUE`
- MERGE pattern: `MERGE (n:AuditgraphNote {id: $id}) SET n.name = $name, n.type = $type`
- For relationships: `MATCH (a), (b) WHERE a.id = $from_id AND b.id = $to_id MERGE (a)-[r:RELATES_TO {id: $rel_id}]->(b) SET r.type = $rel_type`
- Constraint creation requires admin privileges; command can be idempotent (`IF NOT EXISTS` in Neo4j 4.4+)

**Decision**: Generate and execute constraint creation statements at start of sync operation. Use MERGE with property sets for all node and relationship operations. Store stable auditgraph IDs in `id` property.

**Alternatives Considered**:
- Manual CREATE after existence check - rejected: two queries per record, race conditions
- Delete-all-then-recreate - rejected: loses external annotations, high latency
- Optimistic CREATE with error handling - rejected: error logs polluted, transaction rollbacks expensive

---

### R3: Cypher Export File Format and Batching

**Question**: What file format and batching strategy produces deterministic, importable Cypher exports?

**Findings**:
- Standard format: UTF-8 text file with `.cypher` extension
- Transaction batching in file: Wrap groups in `:begin` / `:commit` or use explicit `BEGIN` / `COMMIT` statements
- cypher-shell import: `cat export.cypher | cypher-shell -u user -p password`
- Neo4j Browser compatibility: Can paste and execute batched statements
- Deterministic ordering: Sort entities by ID, then links by (from_id, to_id, link_id) for stable output
- Size limits: Most shells handle scripts up to several GB; transaction size more relevant than file size

**Decision**: Generate single `.cypher` file with explicit `:begin` / `:commit` surrounding each 1000-record batch. Export file statements use MERGE patterns for deterministic and idempotent import behavior. Sort all records deterministically before generation. Include header comment with export metadata (profile, run_id, timestamp, record counts).

**Alternatives Considered**:
- CSV + neo4j-admin import - rejected: requires filesystem access to Neo4j server, not suitable for remote instances
- JSON with APOC procedures - rejected: requires APOC plugin installation, less portable
- Separate files per batch - rejected: user friction assembling imports, determinism harder to verify

---

### R4: Redaction Policy Application to Neo4j Exports

**Question**: How should existing auditgraph redaction policies apply to exported/synced graph data?

**Findings**:
- Existing redactor (auditgraph.utils.redaction) processes JSON payloads and returns redacted dictionaries
- Current policies: PEM keys, JWT tokens, bearer tokens, credential key-value pairs, URL credentials, vendor tokens
- Export flow: Load entity/link → apply redactor → serialize to Cypher
- Sync flow: Same as export before generating MERGE statements
- Performance: Redaction runs during artifact write (ingest/extract stages); export/sync reads already-redacted files

**Decision**: Reuse existing `build_redactor(root, config)` and `redactor.redact_payload()` for all graph records before Cypher generation. This maintains consistency with JSON export and other artifacts.

**Alternatives Considered**:
- Skip redaction (assume already applied) - rejected: export/sync might run on different profile than origin, defense in depth
- Neo4j-specific redaction rules - rejected: unnecessary duplication, existing rules cover Neo4j property scenarios
- Redaction at query time in Neo4j - rejected: secrets already in database, violates auditgraph security model

---

### R5: Error Handling and Connection Resilience

**Question**: What failure modes must be handled for remote database connectivity and how should they surface to users?

**Findings**:
- Common errors: Connection refused, authentication failure, timeout, transaction deadlock, constraint violation
- neo4j driver exceptions: `ServiceUnavailable`, `AuthError`, `TransientError`, `ClientError`
- Recovery strategies: Retry transient errors (deadlocks, timeouts); fail fast on auth/connection errors
- User feedback: Return actionable error message with diagnostic hint (check NEO4J_URI, verify credentials, confirm network)
- Dry-run mode: Execute all logic except final `tx.commit()`; verify connection before iterating records

**Decision**: Wrap driver operations in try/except with specific exception handling. Map driver exceptions to auditgraph error codes (UNAUTHORIZED, CONNECTION_FAILED, TRANSACTION_ERROR). Provide clear diagnostics including environment variable names and connection endpoint. Pre-flight connection check for sync operations (single ping query before batch processing).

**Alternatives Considered**:
- Silent retry with exponential backoff - rejected: user expects fast failure on misconfiguration, long retry delays frustrating
- Generic "sync failed" message - rejected: constitution requires actionable diagnostics
- No dry-run validation - rejected: violates FR-006 requirement and user safety expectations

---

## Research Summary

All technical unknowns resolved. Key decisions:
1. Use official `neo4j` Python driver with write transactions and MERGE operations
2. Generate single `.cypher` file with deterministic ordering and explicit transaction batching
3. Enforce unique constraints on auditgraph IDs for idempotent sync
4. Reuse existing redaction pipeline without modification
5. Fail fast with actionable connection/auth error messages; include dry-run pre-flight checks

No NEEDS CLARIFICATION items remain. Ready for Phase 1 design.

---

# Phase 1: Design & Contracts

## Data Model

See [data-model.md](data-model.md) for complete entity and relationship schemas.

**Data Model Creation Status**: ✅ Generated

## API Contracts

See [contracts/neo4j-export-schema.md](contracts/neo4j-export-schema.md) for Cypher schema and examples.

**Contract Generation Status**: ✅ Generated

## Quickstart Guide

See [quickstart.md](quickstart.md) for step-by-step setup and usage examples.

**Quickstart Creation Status**: ✅ Generated

---

# Phase 2: Task Planning

**Status**: Completed (`tasks.md` generated and aligned)

Phase 1 and Phase 2 artifacts are complete and ready for implementation.
