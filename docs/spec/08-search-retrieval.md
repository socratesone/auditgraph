# Search & Retrieval

## Purpose
Define query types, ranking model, tie-break rules, indexes, and explanation payloads.

## Source material
- [SPEC.md](SPEC.md) Search and Retrieval

## Decisions Required
- Query types required as first-class.
- Dataset scale targets (12 months).
- Local embedding constraints (CPU/GPU, model size).
- Offline-first requirements (semantic search optional or required).
- Deterministic ranking formula and tie-break keys.
- Query response schema and explanation fields.

## Decisions (filled)

### Query Types

- Keyword search
- Hybrid (keyword + semantic)
- Graph traversal (neighbors, paths)
- Show sources for claim

### Dataset Scale Targets

- 12-month target: 10k notes, 50 repos, 1M code symbols

### Embedding Constraints

- CPU-only local embeddings
- Optional
- Model size <= 1.5 GB

### Offline-first Policy

- Core search is fully offline
- Semantic search is optional offline

### Ranking Formula and Tie-break

- Deterministic scoring with stable tie-break keys
- Tie-break order: score, stable_id, normalized path

### Query Response Schema

Required fields:
- `results[]` with `id`, `type`, `score`
- `explanation` object with `matched_terms`, `rule_id` (if applicable), `evidence` references

## Resolved

- Query types, dataset targets, embedding constraints, and offline-first policy defined.
- Ranking formula and deterministic tie-break keys defined.
- Query response schema and explanation fields defined.
