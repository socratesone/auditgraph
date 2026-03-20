# Tasks: NER Entity Extraction

## Phase 1: Core NER Pipeline

### Stage 1: Dependencies and NER Backend
- [ ] **T001** Add spaCy dependency to project
- [ ] **T002** Create setup script for spaCy model download
- [ ] **T003** Implement spaCy NER wrapper (`extract/ner_backend.py`)
- [ ] **T004** Unit tests for NER backend

### Stage 2: NER Extractor Integration
- [ ] **T005** Implement NER entity extractor (`extract/ner.py`)
- [ ] **T006** Add case number regex extractor
- [ ] **T007** Implement canonical name normalization
- [ ] **T008** Add NER config section to `pkg.yaml`
- [ ] **T009** Integration tests for NER extractor

### Stage 3: Pipeline Wiring
- [ ] **T010** Wire NER into `run_extract()` in pipeline runner
- [ ] **T011** Emit MENTIONED_IN links from NER results
- [ ] **T012** Compute and emit CO_OCCURS_WITH links
- [ ] **T013** End-to-end pipeline test with NER

### Stage 4: Neo4j Export
- [ ] **T014** Verify NER entity label mapping in Neo4j records
- [ ] **T015** Export MENTIONED_IN and CO_OCCURS_WITH as Cypher
- [ ] **T016** Add FROM_DOCUMENT relationship export
- [ ] **T017** Neo4j export tests for NER entities

### Stage 5: Query Support
- [ ] **T018** Index NER entity names in BM25
- [ ] **T019** Support entity->chunk->document traversal in neighbor queries
- [ ] **T020** Query tests for NER entities

## Phase 2: Entity Deduplication
- [ ] **T021** Implement fuzzy matching deduplicator
- [ ] **T022** Implement merge logic (canonical selection, alias aggregation)
- [ ] **T023** Wire dedup into pipeline as optional post-extract step
- [ ] **T024** Dedup tests with variant fixtures

## Phase 3: source material Corpus Run
- [ ] **T025** Full pipeline run with NER on source material files
- [ ] **T026** Review and tune extraction quality
- [ ] **T027** Export to Neo4j and validate
- [ ] **T028** Run dedup pass and review
