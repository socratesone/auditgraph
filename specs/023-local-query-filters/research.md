# Research: Local Query Filters & Aggregation

**Date**: 2026-04-06
**Spec**: [spec.md](spec.md)

## Research Questions & Findings

### R1: How does the existing index pipeline work?

**Decision**: Extend `run_index` in `PipelineRunner` to call new index builders after `build_bm25_index`.

**Rationale**: The `run_index` method already loads all entities and calls `build_bm25_index`. Adding `build_type_indexes` and `build_adjacency_index` at the same call site avoids duplicating entity loading. The entities are already materialized in memory at that point (line 731 of `runner.py`).

**Alternatives considered**:
- Separate pipeline stage for type indexes: rejected — adds unnecessary stage ordering complexity.
- Build type indexes during `run_extract`: rejected — entities from all extractors aren't available until after extract completes, and the index stage is the canonical "build derived structures" phase.

### R2: Why is the adjacency index empty?

**Decision**: Create a new `build_adjacency_index` function that reads all link files (not just co-occurrence links).

**Rationale**: The current `run_link` builds the adjacency index only from source co-occurrence links, skipping NER entities entirely. Git-provenance links (`modifies`, `authored_by`, `parent_of`, etc.) are written directly to `links/` during `run_git_provenance` but never included in the adjacency index. The fix is to rebuild adjacency from all link files during `run_index`, not during `run_link`.

**Alternatives considered**:
- Fix `run_link` to include git links: rejected — `run_link` runs before `run_index` and has a different responsibility (creating links, not indexing them). Separating link creation from adjacency indexing follows SRP.
- Lazy adjacency build on first query: rejected — violates determinism (query results would change depending on whether adjacency was built).

### R3: What is the optimal index format for type indexes?

**Decision**: One JSON file per entity type at `indexes/types/<sanitized_type>.json`, containing a flat array of entity IDs.

**Rationale**: With 13 entity types, per-type files are small (commit.json has ~112 IDs, ner_person.json has ~26K IDs). This enables O(1) loading of a single type without parsing the full index. The alternative — a single monolithic file — would work for entity types (123K entries, ~3-5 MB) but not for link types (1.5M entries, 50-100 MB).

**Alternatives considered**:
- Single monolithic JSON file: rejected for links (too large), acceptable for entities but inconsistent.
- SQLite index: rejected — adds dependency, violates plain-text/JSON-only storage philosophy.
- Per-type directories with sharded files: rejected — over-engineering for current scale.

### R4: How should the filter engine handle array fields?

**Decision**: `=` checks membership, `~` checks substring in any element, comparison operators exclude the entity.

**Rationale**: Entity fields like `aliases` (list of strings) and `parent_shas` (list of strings) are top-level but array-valued. Membership semantics for `=` matches user intent ("does this entity have alias X?"). Comparison operators (`>`, `<`) have no clear meaning on arrays, so treating them as missing is the safe default.

**Alternatives considered**:
- Exclude all array fields (treat as missing): rejected — `aliases` is a common search target.
- JSON serialization comparison: rejected — never useful in practice.

### R5: How should MCP default limit be applied?

**Decision**: Apply `limit=100` in the CLI dispatch layer when the command originates from MCP, not in the query function itself.

**Rationale**: The query functions (`list_entities`, `keyword_search`) should be pure — they accept explicit parameters. The MCP default is a transport concern. The CLI `main()` function already knows whether it's being called directly or via MCP subprocess (the MCP adapter calls the CLI as a subprocess). The default limit is applied when `--limit` is not provided.

**Alternatives considered**:
- Default limit in the query function: rejected — makes CLI and MCP behavior diverge at the wrong layer.
- Default limit in MCP adapter: acceptable alternative, but applying it at CLI dispatch keeps the "no limit = unlimited" contract clean for the query functions.

### R6: How should `--count` interact with `--limit`?

**Decision**: `--count` always reflects total matches before limit/offset is applied.

**Rationale**: This is consistent with the MCP `total_count` field (FR-063) and the only interpretation where combining `--count --limit` is useful. A post-limit count is trivially derivable from `len(results)`.

**Alternatives considered**:
- Post-limit count: rejected — trivially computed from result length, adds no information.
- Mutually exclusive flags: rejected — limits composability without clear benefit.
