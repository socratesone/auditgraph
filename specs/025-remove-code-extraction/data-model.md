# Data Model: Remove Code Extraction, Migrate File Entity Creation to Git Provenance

**Date**: 2026-04-07
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

This spec is a scope-narrowing + bug-fix change. The data model is **almost entirely unchanged** — the file entity schema is preserved exactly per clarification Q1. The only changes are:

1. The set of entity types produced by the `git_provenance` stage gains `file`.
2. The set of entity types produced by the `extract` stage loses `file`.
3. Several config keys and parser routings are removed (no schema impact).

## File Entity (creator changed, schema unchanged)

A graph node representing a file path that appears in the repository's git history. The schema is byte-for-byte identical to the existing output of `extract.code_symbols.v1` — only the creator changes.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier. Derived as `entity_id(canonical_key)` via `auditgraph.storage.hashing.entity_id`. Same hash function used by `git/materializer.py:build_links()` to compute `modifies` link `to_id` values, guaranteeing the IDs match. |
| `type` | string | Always `"file"`. |
| `name` | string | The file's basename (e.g., `ner.py` for `auditgraph/extract/ner.py`). |
| `canonical_key` | string | `"file:<normalized_path>"`. The string passed to `entity_id()` to produce the entity's `id`. Determines uniqueness — two file entities with the same canonical key are the same entity. |
| `source_path` | string | The full normalized path of the file relative to the repository root (e.g., `auditgraph/extract/ner.py`). Identical to the `source_path` field that `extract_code_symbols` produces today. |

### Lifecycle

| Stage | Behavior |
|-------|----------|
| **Today (before this change)** | Created by `extract.code_symbols.v1` only for files matching `.py .js .ts .tsx .jsx`. Git provenance emits `modifies` links to file entity IDs but never creates the entities. Result: dangling references for every non-code file. |
| **Phase A end state** | Created by both `extract.code_symbols.v1` AND the new `build_file_nodes()` in git provenance. The two creators produce identical entities for the overlapping subset (code files in git history). The `build_file_nodes` creator covers ALL files in git history, fixing dangling references. |
| **Phase B end state** | Created exclusively by `build_file_nodes()` in git provenance. `extract.code_symbols.v1` is deleted. The set of file entities equals the set of distinct paths across all selected commits' `files_changed` lists. |

### Identity & uniqueness

- One file entity per unique `canonical_key`. Two paths that normalize to the same string produce the same entity.
- The `id` is fully determined by the `canonical_key` via `entity_id()` (a SHA-256 over the canonical key). Identical canonical keys produce identical IDs across runs and machines.
- Path normalization is via `auditgraph.normalize.paths.normalize_path()`, the same function `extract_code_symbols` uses today. Phase A's `build_file_nodes` MUST use the same normalization to guarantee ID matching.

### Determinism

- The output of `build_file_nodes` is sorted by entity ID (matching the convention of other `build_*_nodes` functions).
- The set of paths is collected during the walk (deduplication), then sorted before entity dict construction.
- Two runs of `build_file_nodes` on the same `selected_commits` produce byte-identical entity lists.

### Field-level migration notes

| Field | Old creator | New creator | Migration required? |
|-------|-------------|-------------|---------------------|
| `id` | `entity_id("file:" + normalized_path)` | `entity_id("file:" + normalized_path)` | No — identical |
| `type` | `"file"` | `"file"` | No — identical |
| `name` | `path.name` | `path.name` (basename of `file_path` string) | No — identical |
| `canonical_key` | `f"file:{normalized}"` | `f"file:{normalized}"` | No — identical |
| `source_path` | `normalized` (str) | `normalized` (str) | No — identical |

**Zero schema migration. Zero new fields. Zero deleted fields. Per clarification Q1.**

## Entity Type Inventory

Pre-change vs. post-change inventory of every entity type produced by every pipeline stage:

| Entity Type | Today's Creator | Post-Change Creator |
|-------------|----------------|---------------------|
| `ag:note` | `run_extract` (note extractor) | `run_extract` (unchanged) |
| `ag:section` | `run_extract` (content extractor) | `run_extract` (unchanged) |
| `ag:technology` | `run_extract` (content extractor) | `run_extract` (unchanged) |
| `ag:reference` | `run_extract` (content extractor) | `run_extract` (unchanged) |
| `ner:person` / `ner:org` / `ner:gpe` / `ner:date` / `ner:law` / `ner:money` / `ner:case_number` | `run_extract` (NER, opt-in) | `run_extract` (unchanged) |
| `commit` | `run_git_provenance` | `run_git_provenance` (unchanged) |
| `author_identity` | `run_git_provenance` | `run_git_provenance` (unchanged) |
| `tag` | `run_git_provenance` | `run_git_provenance` (unchanged) |
| `repository` | `run_git_provenance` | `run_git_provenance` (unchanged) |
| `ref` | `run_git_provenance` | `run_git_provenance` (unchanged) |
| **`file`** | **`run_extract` (`extract_code_symbols`)** | **`run_git_provenance` (`build_file_nodes`)** ← only change |

## Link Type Inventory (unchanged)

No link types are added, removed, or modified by this spec. The existing link types continue to work exactly as today:

| Link Type | Direction | Effect of this spec |
|-----------|-----------|---------------------|
| `relates_to` | entity → entity (co-occurrence) | Unchanged |
| `MENTIONED_IN` | NER entity → chunk | Unchanged |
| `CO_OCCURS_WITH` | NER entity → NER entity | Unchanged |
| `modifies` | commit → file | **Targets resolve to real entities for ALL file types after Phase A** (today: only for code-extension subset) |
| `parent_of` | child commit → parent commit | Unchanged |
| `authored_by` | commit → author_identity | Unchanged |
| `contains` | repository → commit | Unchanged |
| `tags` | tag → commit | Unchanged |
| `on_branch` | head commit → ref | Unchanged |
| `succeeded_from` | new file → old file (rename detection) | **Both endpoints now resolve** for all renamed paths after Phase A (today: usually dangling) |

## Removed Concepts

These data-model concepts are eliminated entirely by Phase B:

| Concept | Where it lived | Why removed |
|---------|---------------|-------------|
| `parser_id == "text/code"` | `auditgraph/ingest/policy.py:PARSER_BY_SUFFIX`, `auditgraph/ingest/parsers.py:parse_file` | After Phase B no parser stage handles code files; routing them to a dedicated `text/code` parser_id is misleading dead code. |
| `extract_code_symbols` function and module | `auditgraph/extract/code_symbols.py` | Replaced by `build_file_nodes` in git provenance. |
| `extract.code_symbols.v1` rule_id | Implicitly referenced by the rule name in extracted entities' `provenance.created_by_rule` field, if any | After Phase B, no entity carries this rule_id because no entity is produced by that path. |
| `chunk_code.enabled` config flag | `config/pkg.yaml:profiles.<n>.ingestion.chunk_code`, `auditgraph/config.py:DEFAULT_CONFIG`, `auditgraph/ingest/parsers.py:parse_file` (`chunk_code_enabled` option), `auditgraph/pipeline/runner.py` (parse_options wiring × 2 sites) | The flag was added in the quality sweep to make code chunking opt-in. Phase B removes the underlying capability, so the flag has nothing to gate. |
| `tests/test_code_chunking_opt_in.py` | The test file itself | Tests the `chunk_code.enabled` feature being removed. |

## Storage Layout (unchanged)

```
.pkg/profiles/<profile>/
  entities/
    <shard>/
      ent_<sha256>.json    # file entities live here, sharded by ID prefix
                           # (creator changes; layout, sharding, schema all unchanged)
  links/
    <shard>/
      lnk_<sha256>.json    # modifies, authored_by, etc. (unchanged)
  indexes/
    types/
      file.json            # type-index entry (unchanged; populated automatically by Spec 023's index stage)
```

The on-disk layout for file entities is identical pre- and post-change. The shard path is computed from the entity ID, the entity ID is computed from the canonical key, and the canonical key is identical between old and new creators. A user inspecting `.pkg/profiles/default/entities/ab/ent_ab123...json` after the change will see the same file content they would have seen before — minus the dangling-reference bug for non-code files.

## Test Fixtures

Existing test fixtures that contain `type=file` entities (verified via grep):

| Fixture | Schema | Compatible with new code? |
|---------|--------|---------------------------|
| `tests/fixtures/spec023/entities/ee/ent_ee55ff66aa11.json` | `type=file`, `canonical_key=file:src/auth/session.py`, `source_path=...` | Yes — schema match |
| `tests/fixtures/spec023/entities/dd/ent_dd44ee55ff66.json` | `type=file`, `canonical_key=file:src/auth/login.py`, `source_path=...` | Yes — schema match |
| `tests/support.py` (helper) | Constructs `{"type": "file", ...}` for unit tests | Yes — schema match |
| `tests/test_spec011_export_redaction.py` | Constructs file entities for export tests | Yes — schema match |
| `tests/test_spec011_export_metadata.py` | Same | Yes — schema match |

No fixture updates required. The schema commitment in clarification Q1 was made specifically to avoid this kind of cascade.

## Determinism Guarantees (unchanged)

- File entity IDs are deterministic (function of canonical key).
- File entity ordering on disk is deterministic (sharded by ID, alphabetical).
- The `outputs_hash` of `run_git_provenance` is deterministic (sorted entity IDs and link IDs, consistent with the existing implementation).
- Two runs of `auditgraph rebuild` on the same workspace + same git history produce byte-identical `.pkg/profiles/<profile>/` contents for the entity files.
