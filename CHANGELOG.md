# Changelog

## Unreleased

### Removed
- **Source code symbol extraction is permanently out of scope (Spec 025).** Auditgraph is a documents + provenance tool. Files with `.py`, `.js`, `.ts`, `.tsx`, `.jsx` extensions are no longer ingested by default — they are skipped at the ingest stage with reason `unsupported_extension`. Specifically:
  - Deleted `auditgraph/extract/code_symbols.py` entirely. The function was named `extract_code_symbols` but only ever produced one opaque `file` entity per source file with no real symbol information — the name was a lie about what it did.
  - Deleted the `text/code` parser_id from `auditgraph/ingest/policy.py:PARSER_BY_SUFFIX` and the corresponding entries from `DEFAULT_ALLOWED_EXTENSIONS`.
  - Deleted the `chunk_code.enabled` opt-in config flag (added briefly during the post-Spec-023 quality sweep) and its supporting wiring across `auditgraph/pipeline/runner.py`, `auditgraph/ingest/parsers.py`, `auditgraph/config.py`, and `config/pkg.yaml`.
  - Deleted `tests/test_code_chunking_opt_in.py`.
  - Deleted the now-dead `build_entity` function from `auditgraph/extract/entities.py` (its only call site was inside the deleted code symbols loop).
  - For code structure navigation, use a language-aware tool: LSP, ctags, ripgrep, treesitter-based analyzers, `tldr`, your IDE, or any of the many existing code intelligence products.
  - **Migration**: existing workspaces with file entities for `.py` etc. will see those entities re-created with identical IDs by git provenance (Spec 025 fix below) for any path that exists in git history. File entities for code files NOT in git history will not be re-created — to query the new state, run `auditgraph rebuild` after upgrading.

### Fixed
- **Pre-existing dangling-reference bug in git provenance (Spec 025).** Before this change, git provenance emitted `modifies` links pointing at file entity IDs computed via `entity_id(f"file:{path}")`, but the target entities were only ever created by `extract_code_symbols` and only for the 5 code extensions. For every non-code file in any commit's history (markdown, YAML, README, PDF, configs, etc.), the `modifies` link was a dangling reference. After this change, file entity creation is moved into `auditgraph/git/materializer.py:build_file_nodes` and produces an entity for **every** distinct path in commit history, regardless of file extension. `auditgraph neighbors <commit_id> --edge-type modifies` now returns resolvable file entities for ALL modified files. The IDs match what existing `modifies` links point at, so existing workspaces continue to work without migration.

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
