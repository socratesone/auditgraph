# Research: NER Entity Extraction

## Current Codebase Analysis

### Entity System (Existing)

Entities are plain dicts with these keys: `id`, `type`, `name`, `canonical_key`, `aliases`, `provenance`, `refs`. No schema registration required — any type string is accepted. The Neo4j label is auto-generated from the type string via `map_entity_type_to_label()` in `neo4j/records.py`.

### Integration Points

1. **`run_extract()` in `pipeline/runner.py:316-436`** — Main extraction loop. Iterates source records, calls extractors, writes entities. New NER extractor plugs in here.
2. **Chunk artifacts in `.pkg/profiles/default/chunks/`** — NER reads from these. Each chunk has `text`, `document_id`, `source_path`, `source_hash`.
3. **Entity storage in `.pkg/profiles/default/entities/`** — NER writes NamedEntity dicts here using existing `write_entities()`.
4. **Link storage in `.pkg/profiles/default/links/`** — Currently unused (0 links in current graph). NER writes MENTIONED_IN and CO_OCCURS_WITH here.
5. **Plugin system stub** — `auditgraph/plugins/registry.py` has `load_extractor_plugins()` but is not wired. Consider for Phase 2.

### Existing Unwired Code

`extract/content.py` defines `extract_content_entities()` which produces `ag:section`, `ag:technology`, `ag:reference` entities from markdown. It works but has zero call sites in `runner.py`. Wiring this is a separate low-effort improvement.

## source material Corpus Characteristics

### Source Data Quality

| Dataset | Size | OCR Quality | Notes |
|---------|------|-------------|-------|
| DataSet_1 | 144K | Low | Short fragments, document IDs |
| DataSet_2 | 36K | Very Low | Mostly OCR artifacts |
| DataSet_3 | 280K | Medium | Mixed quality |
| DataSet_4 | 3.2M | Good | Largest, most text |
| DataSet_5 | 24K | Good | Short, clear text |
| DataSet_6 | 472K | Good | Legal documents |
| DataSet_7 | 672K | Good | Legal documents |
| 1332-16 | 28K | Good | Court filing |

### Expected Entity Types

Based on the corpus content (legal documents, court filings, depositions):

- **PERSON**: Names of individuals (defendants, witnesses, attorneys, judges)
- **ORG**: Law firms, companies, government agencies, foundations
- **GPE**: Cities, states, countries mentioned in proceedings
- **DATE**: Filing dates, event dates, deposition dates
- **LAW**: Statute citations, legal references
- **CASE_NUMBER**: Docket numbers (e.g., "08-cv-01234")
- **MONEY**: Financial amounts in settlements, transactions

### OCR Noise Patterns

From DjVu text sample:
```
casein JIE -NY- 3097571  & ar
PHOTOGRAPHER
LOCATION 9 East 'II a
New York, AY aa
EFTA00000001
```

Common noise: random characters, broken words, misread punctuation, document control numbers (EFTA*). The quality gate (`quality_score >= 0.3`) will filter the worst chunks.

## spaCy Model Selection

| Model | Size | Accuracy (F1) | Speed | Recommendation |
|-------|------|----------------|-------|----------------|
| `en_core_web_sm` | 12MB | ~85% | Fast | Default/CI |
| `en_core_web_md` | 40MB | ~87% | Medium | Good balance |
| `en_core_web_lg` | 560MB | ~88% | Slower | Better for noisy text |
| `en_core_web_trf` | 438MB | ~90% | Slowest | Best accuracy, needs GPU |

Recommendation: Default to `en_core_web_sm` for quick iteration, `en_core_web_lg` for production runs on the source material corpus. The `trf` model requires torch and is heavyweight.

## Alternative Approaches Considered

1. **LLM-based extraction** — Higher accuracy on noisy text but non-deterministic, expensive, slow. Deferred to Phase 2 behind `llm.enabled` flag.
2. **Regex-only extraction** — Deterministic but low recall for names. Used only for CASE_NUMBER.
3. **Hugging Face NER models** — Similar to spaCy trf but different ecosystem. spaCy preferred for pipeline integration.
4. **Custom fine-tuned model** — Best accuracy but requires labeled training data. Phase 3 consideration.
