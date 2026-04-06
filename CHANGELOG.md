# Changelog

## Unreleased

### Added
- **Local query filters & aggregation (Spec 023).** You can now browse, filter, sort, and count entities directly from the CLI without writing post-processing scripts.
  - New `auditgraph list` command — browse entities without a keyword search. Supports `--type`, `--where "field<op>value"`, `--sort`, `--desc`, `--limit`, `--offset`, `--count`, and `--group-by`.
  - Extended `auditgraph query` with the same filter/sort/limit/aggregation flags so you can narrow BM25 search results.
  - Extended `auditgraph neighbors` with `--edge-type` and `--min-confidence` to filter graph traversals by relationship type and confidence threshold.
  - Filter operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~` (substring contains). Numeric values are auto-detected; array fields support membership semantics for `=`/`!=` and substring search for `~`.
  - New MCP tools: `ag_list` (with `total_count`/`truncated` response envelope and a default `limit=100`), and the `ag_query` and `ag_neighbors` tools now accept the new filter parameters.
  - New per-type indexes built during the `index` pipeline stage: `indexes/types/<type>.json` and `indexes/link-types/<type>.json` enable selective entity loading without scanning the full corpus.
  - The forward adjacency index (`indexes/graph/adjacency.json`) is now rebuilt from **all** link files, including git-provenance links (commits, authors, modifies, parent_of) — these were previously missing from graph traversals.
  - 161 new tests covering the index builders, filter engine, sort/pagination, aggregation, edge cases, and MCP tool surface.
- Neo4j export/sync feature scaffolding and CLI commands (`export-neo4j`, `sync-neo4j`).
- Neo4j records/cypher builder/export/sync modules under `auditgraph/neo4j/`.
- Targeted Neo4j test suite (`tests/test_neo4j_*.py`) and fixtures.
- Documentation for Neo4j setup and usage in README, QUICKSTART, MCP guide, and environment setup docs.
