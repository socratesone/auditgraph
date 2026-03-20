# Data Model: NER Entity Extraction

## Entities

### NamedEntity

- `id` (string, stable) — `ent_<sha256("ner:<type>:<canonical_name>")>`
- `type` (string) — one of: `ner:person`, `ner:org`, `ner:gpe`, `ner:date`, `ner:law`, `ner:case_number`, `ner:money`
- `name` (string) — canonical form of the entity name
- `canonical_key` (string) — `ner:<type>:<lowercased_normalized_name>`
- `aliases` (array[string]) — all surface forms seen in text (e.g., ["Jeffrey source material", "J. source material", "source material"])
- `mention_count` (integer) — total number of chunk mentions
- `provenance` (object) — `{ "rule": "ner.spacy.v1", "model": "<model_name>", "confidence_mean": <float> }`
- `profile` (string) — active profile name
- `source_paths` (array[string]) — unique source documents containing this entity

### Neo4j Labels

Entity type strings map to Neo4j labels via existing `map_entity_type_to_label()`:

| Entity type | Neo4j label |
|-------------|-------------|
| `ner:person` | `:AuditgraphNerPerson` |
| `ner:org` | `:AuditgraphNerOrg` |
| `ner:gpe` | `:AuditgraphNerGpe` |
| `ner:date` | `:AuditgraphNerDate` |
| `ner:law` | `:AuditgraphNerLaw` |
| `ner:case_number` | `:AuditgraphNerCaseNumber` |
| `ner:money` | `:AuditgraphNerMoney` |

## Relationships

### MENTIONED_IN (NamedEntity -> Chunk)

- `source_entity_id` (string) — the NamedEntity ID
- `target_chunk_id` (string) — the Chunk ID
- `rule` (string) — `"ner.mention.v1"`
- `confidence` (float) — spaCy confidence score for this mention
- `span_start` (integer) — character offset in chunk text
- `span_end` (integer) — character offset in chunk text
- `surface_form` (string) — exact text matched

### CO_OCCURS_WITH (NamedEntity <-> NamedEntity)

- `source_entity_id` (string) — entity A
- `target_entity_id` (string) — entity B
- `rule` (string) — `"ner.cooccurrence.v1"`
- `confidence` (float) — 1.0 (deterministic: both appear in same chunk)
- `shared_chunk_count` (integer) — number of chunks where both entities appear
- `shared_chunk_ids` (array[string]) — chunk IDs of co-occurrence (capped at 100)

### FROM_DOCUMENT (Chunk -> Document)

Already exists implicitly via `document_id` on ChunkRecord. The Neo4j export should emit this as an explicit relationship for traversal.

## Identity and Stability Rules

- **NamedEntity ID**: deterministic from `ner:<type>:<canonical_name>` — same entity in different chunks produces the same node.
- **Relationship ID**: deterministic from `sha256(source_id + ":" + target_id + ":" + rule)`.
- **Canonical name normalization**: lowercase, collapse whitespace, strip titles (Mr./Mrs./Dr./Hon.), strip trailing punctuation.
- **Type mapping from spaCy labels**: `PERSON` -> `ner:person`, `ORG` -> `ner:org`, `GPE` -> `ner:gpe`, `DATE` -> `ner:date`, `LAW` -> `ner:law`, `MONEY` -> `ner:money`.
- **CASE_NUMBER**: custom regex pattern `\b\d{2,4}-[A-Z]{2,4}-\d{3,8}\b` and variants, not from spaCy.

## OCR Quality Gate

Before NER processing, each chunk is scored:

```
quality_score = len([c for c in text if c.isalnum()]) / max(len(text), 1)
```

- `quality_score >= 0.3`: process normally
- `quality_score < 0.3`: skip chunk, log as `ner_skipped_low_quality`

## Storage Layout

```
.pkg/profiles/default/
  entities/
    <shard>/
      ent_<hash>.json          # NamedEntity (same dir as existing entities)
  links/
    <shard>/
      lnk_<hash>.json          # MENTIONED_IN and CO_OCCURS_WITH relationships
```

Follows existing sharding convention (first 2 chars of ID).
