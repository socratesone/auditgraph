# Implementation Plan: NER Entity Extraction

**Spec**: 018-ner-entity-extraction
**Branch**: `018-ner-entity-extraction`
**Base**: `017-pdf-doc-ingestion`

## Phase 1: Core NER Pipeline (P1 stories)

### Stage 1: Dependencies and NER Backend

| Task | File(s) | Description |
|------|---------|-------------|
| T001 | `pyproject.toml` / `requirements.txt` | Add spaCy dependency (`spacy>=3.7,<4`) |
| T002 | `scripts/setup-ner.sh` | Script to download spaCy model (`en_core_web_sm` default, `en_core_web_trf` for accuracy) |
| T003 | `auditgraph/extract/ner_backend.py` | spaCy NER wrapper: load model, extract entities from text, return structured results |
| T004 | `tests/test_ner_backend.py` | Unit tests for NER backend with fixture text |

### Stage 2: NER Extractor Integration

| Task | File(s) | Description |
|------|---------|-------------|
| T005 | `auditgraph/extract/ner.py` | NER entity extractor: iterate chunks, quality-gate, call backend, produce NamedEntity dicts |
| T006 | `auditgraph/extract/ner.py` | Case number regex extractor (custom, not spaCy) |
| T007 | `auditgraph/extract/ner.py` | Canonical name normalization (lowercase, strip titles, collapse whitespace) |
| T008 | `config/pkg.yaml` | Add `ner` section under `extraction`: `enabled: true`, `model: en_core_web_sm`, `quality_threshold: 0.3`, `entity_types: [PERSON, ORG, GPE, DATE, LAW, MONEY]` |
| T009 | `tests/test_ner_extractor.py` | Integration tests: fixture chunks -> entity extraction -> verify output structure |

### Stage 3: Pipeline Wiring

| Task | File(s) | Description |
|------|---------|-------------|
| T010 | `auditgraph/pipeline/runner.py` | Wire `extract_ner_entities()` into `run_extract()` — call after existing extractors, merge entities |
| T011 | `auditgraph/pipeline/runner.py` | Emit MENTIONED_IN links from NER results into the links directory |
| T012 | `auditgraph/pipeline/runner.py` | Compute CO_OCCURS_WITH from chunk-level entity co-occurrence, emit as links |
| T013 | `tests/test_ner_pipeline.py` | End-to-end test: ingest fixture -> extract -> verify entities and links in .pkg |

### Stage 4: Neo4j Export

| Task | File(s) | Description |
|------|---------|-------------|
| T014 | `auditgraph/neo4j/records.py` | Ensure NER entity types produce correct labels (should work automatically via `map_entity_type_to_label`) |
| T015 | `auditgraph/neo4j/export.py` | Load and export MENTIONED_IN and CO_OCCURS_WITH relationships as Cypher |
| T016 | `auditgraph/neo4j/export.py` | Add FROM_DOCUMENT relationship export (Chunk -> Document) |
| T017 | `tests/test_ner_neo4j_export.py` | Test: verify Cypher output includes NER nodes and all three relationship types |

### Stage 5: Query Support

| Task | File(s) | Description |
|------|---------|-------------|
| T018 | `auditgraph/query/keyword.py` | Index NER entity names in BM25 index for search |
| T019 | `auditgraph/query/neighbors.py` | Support entity -> chunk -> document traversal in neighbor queries |
| T020 | `tests/test_ner_query.py` | Test: query entity name, verify results include entity + linked chunks |

## Phase 2: Entity Deduplication (P3 story)

| Task | File(s) | Description |
|------|---------|-------------|
| T021 | `auditgraph/extract/dedup.py` | Fuzzy matching deduplicator: Levenshtein distance + token overlap scoring |
| T022 | `auditgraph/extract/dedup.py` | Merge logic: canonical selection (longest form), alias aggregation, relationship transfer |
| T023 | `auditgraph/pipeline/runner.py` | Wire dedup as optional post-extract step (`ner.dedup_enabled: true`) |
| T024 | `tests/test_ner_dedup.py` | Test: fixture variants -> dedup -> verify single canonical entity with aliases |

## Phase 3: source material Corpus Run

| Task | File(s) | Description |
|------|---------|-------------|
| T025 | — | Full pipeline run on source material DjVu text files with NER enabled |
| T026 | — | Review extracted entities, tune quality threshold if needed |
| T027 | — | Export to Neo4j and validate graph structure |
| T028 | — | Run dedup pass, review merge quality |

## Dependencies

```
T001 -> T002 -> T003 -> T004
T003 -> T005 -> T006 -> T007 -> T008 -> T009
T009 -> T010 -> T011 -> T012 -> T013
T013 -> T014 -> T015 -> T016 -> T017
T013 -> T018 -> T019 -> T020
T020 -> T021 -> T022 -> T023 -> T024
T024 -> T025 -> T026 -> T027 -> T028
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| spaCy model too large for CI | Medium | Low | Default to `en_core_web_sm` (12MB), `trf` model optional |
| OCR noise degrades NER accuracy | High | Medium | Quality gate + dedup pass; consider fine-tuning in Phase 2 |
| Entity explosion (thousands of DATE entities) | High | Medium | Cap entity types in config; filter by mention_count threshold |
| CO_OCCURS_WITH relationship explosion (N^2 per chunk) | Medium | High | Cap co-occurrence pairs per chunk; only emit for PERSON/ORG/GPE |
| spaCy model not installed at runtime | Medium | Medium | Graceful skip with warning when model unavailable; NER is optional |

## Estimated Graph Size (source material Corpus)

Based on ~5,375 chunks of 200 tokens each:

| Artifact | Estimated Count |
|----------|----------------|
| NamedEntity (PERSON) | 500-2,000 |
| NamedEntity (ORG) | 200-800 |
| NamedEntity (GPE) | 100-500 |
| NamedEntity (DATE) | 500-2,000 |
| MENTIONED_IN relationships | 5,000-20,000 |
| CO_OCCURS_WITH relationships | 2,000-10,000 |
| Total graph nodes | ~8,000-15,000 |
| Total graph relationships | ~7,000-30,000 |
