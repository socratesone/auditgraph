# Feature Specification: Search and Retrieval

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Day-1 search supports keyword queries over entity names and graph traversal for neighbors
and why-connected. Ranking is deterministic with explicit tie-break keys.

## Supported Queries
- Keyword search (`query` command)
- Node view (`node` command)
- Neighbors traversal (`neighbors` command)
- Why-connected (`why-connected` command)

## Ranking
- Score rounding uses `profiles.<name>.search.ranking.score_rounding`.
- Tie-break keys are explicit and deterministic (entity id).

## Response Schema
Keyword results MUST include:
- `id`, `score`
- `explanation.matched_terms`
- `explanation.tie_break`

Neighbors response MUST include:
- `center_id`, `neighbors[]`

Why-connected response MUST include:
- `path[]` (may be empty)

## Index Artifacts
- Keyword index: `.pkg/profiles/<profile>/indexes/bm25/index.json`
- Graph adjacency: `.pkg/profiles/<profile>/indexes/graph/adjacency.json`

## Acceptance Tests
- Keyword search returns explanation fields.
- Equal scores are ordered deterministically by tie-break.
- Missing index returns empty results without error.

## Success Criteria
- 100% of query responses include required fields.
