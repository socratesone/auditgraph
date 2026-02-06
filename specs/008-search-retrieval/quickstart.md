# Quickstart: Search and Retrieval

## Goal

Use this spec to understand query types, ranking policy, and explanation payloads.

## Steps

1. Review [specs/008-search-retrieval/spec.md](specs/008-search-retrieval/spec.md) for query types and requirements.
2. Read [specs/008-search-retrieval/data-model.md](specs/008-search-retrieval/data-model.md) for query/result entities and validation rules.
3. Use [specs/008-search-retrieval/contracts/search-retrieval.openapi.yaml](specs/008-search-retrieval/contracts/search-retrieval.openapi.yaml) to align response fields with API consumers.
4. Confirm deterministic ranking and tie-break policy in the spec and [docs/spec/08-search-retrieval.md](docs/spec/08-search-retrieval.md).

## Success Check

- Each query type has documented response fields.
- Results include explanations with evidence references.
