# Feature Specification: Named Entity Recognition (NER) Extraction

**Feature Branch**: `018-ner-entity-extraction`
**Created**: 2026-03-18
**Status**: Draft
**Input**: User description: "Extract named entities (people, organizations, locations, dates, case numbers) from ingested document chunks and create graph nodes with MENTIONED_IN relationships to enable knowledge graph queries across the source material files corpus"

## Clarifications

### Session 2026-03-18

- Q: Which NER backend should be used? → A: spaCy with `en_core_web_trf` (transformer-based) for accuracy on OCR-degraded legal text. Fall back to `en_core_web_sm` if GPU unavailable.
- Q: Should NER run on chunks or full document text? → A: Run on chunks — they are already token-bounded and preserve provenance linkage.
- Q: Should entity deduplication happen at extraction time or as a separate stage? → A: Separate post-extraction merge stage. Extract first, deduplicate second.
- Q: How to handle OCR noise in entity extraction? → A: Pre-filter chunks below a quality threshold (ratio of alphanumeric to total characters). Skip chunks that are predominantly garbage.
- Q: Should this be LLM-based or rule-based? → A: spaCy NER (rule-based + statistical) for Phase 1. LLM-based extraction (via the existing `llm.enabled` config flag) is Phase 2 scope.
- Q: What entity types are in scope? → A: PERSON, ORG, GPE (geopolitical entity), DATE, LAW (legal references), CASE_NUMBER (custom pattern), MONEY.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract named entities from document chunks (Priority: P1)

As a user, I can run entity extraction on ingested documents and the system produces named entity nodes linked to the chunks they appear in.

**Why this priority**: Without entity extraction, the graph is just a bag of text chunks with no semantic structure.

**Independent Test**: Ingest a fixture document with known entities, run extract, verify entity nodes are created with correct types and MENTIONED_IN relationships to source chunks.

**Acceptance Scenarios**:

1. **Given** ingested document chunks containing names and organizations, **When** the extract stage runs with NER enabled, **Then** entity nodes are created for each unique entity with type, name, and canonical form.
2. **Given** an entity name appearing in multiple chunks, **When** extraction completes, **Then** a single entity node exists with MENTIONED_IN relationships to all containing chunks.
3. **Given** a chunk with OCR quality below the configured threshold, **When** NER runs, **Then** the chunk is skipped with a logged reason.

---

### User Story 2 - Query entities and their connections (Priority: P1)

As a user, I can search for a person or organization by name and see all documents, chunks, and co-occurring entities.

**Why this priority**: Entity queries are the core value proposition of a knowledge graph over a document store.

**Independent Test**: After extraction, query for a known person name and verify results include the entity, its source chunks, source documents, and co-occurring entities.

**Acceptance Scenarios**:

1. **Given** extracted entities, **When** the user queries by entity name, **Then** results include the entity node, all MENTIONED_IN chunks, and their parent documents.
2. **Given** two entities that appear in the same chunk, **When** the user queries co-occurrences, **Then** a CO_OCCURS_WITH relationship (or traversal) connects them.

---

### User Story 3 - Export NER entities to Neo4j (Priority: P2)

As a user, I can export the enriched graph including NER entities and their relationships to Neo4j.

**Why this priority**: Neo4j is the target visualization and query platform.

**Independent Test**: Run export-neo4j after NER extraction and verify the Cypher output includes entity nodes with correct labels and MENTIONED_IN relationships.

**Acceptance Scenarios**:

1. **Given** extracted entities and relationships, **When** export-neo4j runs, **Then** the Cypher file includes MERGE statements for entity nodes and MENTIONED_IN/CO_OCCURS_WITH relationships.
2. **Given** entity nodes, **When** loaded into Neo4j, **Then** Cypher queries like `MATCH (p:Person)-[:MENTIONED_IN]->(c:Chunk)-[:FROM_DOCUMENT]->(d:Document) RETURN p.name, d.source_path` return correct results.

---

### User Story 4 - Entity deduplication and merge (Priority: P3)

As a user, I can run a deduplication pass that merges variant spellings and partial names into canonical entities.

**Why this priority**: OCR text produces many spelling variants of the same entity. Without dedup, the graph has fragmented nodes.

**Independent Test**: Create fixtures with known variants ("Jeffrey source material", "J. source material", "source material, Jeffrey"), run dedup, verify they merge into one canonical entity.

**Acceptance Scenarios**:

1. **Given** multiple entity nodes with similar names, **When** dedup runs, **Then** variants are merged under a canonical entity with aliases preserved.
2. **Given** a merged entity, **When** queried, **Then** all original MENTIONED_IN relationships are preserved on the canonical node.

---

## Constraints

- **Determinism**: Entity IDs must be deterministic (content-addressed) following the `ent_<sha256(canonical_key)>` pattern.
- **Idempotency**: Re-running extraction on unchanged chunks must produce identical results.
- **No LLM dependency for Phase 1**: spaCy statistical models only. The `llm.enabled: false` config flag must be respected.
- **Backward compatibility**: Existing entity types (file, ag:note, document, chunk) must not be affected.
- **OCR tolerance**: The extractor must handle noisy OCR text gracefully — skip garbage, don't crash on encoding issues.

## Out of Scope (Phase 1)

- LLM-based entity extraction (Phase 2, behind `llm.enabled` flag)
- Relationship extraction beyond co-occurrence (e.g., "X employed Y")
- Temporal reasoning on dates
- Cross-document entity resolution using external knowledge bases
- Real-time/streaming extraction
