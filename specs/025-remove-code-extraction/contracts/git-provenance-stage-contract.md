# Contract: `run_git_provenance` Stage (Post-Change)

**Spec**: [025-remove-code-extraction](../spec.md)
**Date**: 2026-04-07

This contract documents the externally observable behavior of the `run_git_provenance` pipeline stage after this spec lands. It is the agreement between the stage and the rest of the pipeline.

## Inputs (unchanged)

| Input | Source | Type |
|-------|--------|------|
| `root` | CLI / pipeline arg | `pathlib.Path` (workspace root containing `.git/`) |
| `config` | Loaded from `config/pkg.yaml` or user-supplied YAML | `auditgraph.config.Config` |
| `run_id` | Pipeline-supplied (from earlier stage manifest) | `str` |

## Pre-conditions (unchanged)

1. The repository at `root` MUST be a valid git repository readable by `dulwich`.
2. The `run_id` MUST correspond to a completed `ingest` stage with a manifest at `pkg_root/runs/<run_id>/ingest-manifest.json`.
3. `config.profile().git_provenance.enabled` MUST be `true` for the stage to do work. When `false`, the stage returns `StageResult(stage="git-provenance", status="skipped", detail={"reason": "disabled"})` and writes nothing.

## Outputs

### Entities written (one new type)

The stage writes JSON files to `pkg_root/entities/<shard>/<entity_id>.json` for the following entity types. **Bold** indicates new behavior introduced by this spec.

| Entity Type | Pre-change count source | Post-change count source |
|-------------|------------------------|--------------------------|
| `commit` | One per `selected_commits[i]` | Same |
| `author_identity` | One per distinct author email | Same |
| `tag` | One per git tag (lightweight or annotated) | Same |
| `repository` | Exactly one for the repo root | Same |
| `ref` | One per git branch | Same |
| **`file`** | **Not created (dangling references)** | **One per distinct file path across all selected commits' `files_changed` lists** |

### File entity schema (new responsibility, existing schema)

Each file entity written by `run_git_provenance` MUST have these fields and ONLY these fields:

```json
{
  "id": "ent_<sha256>",
  "type": "file",
  "name": "<basename>",
  "canonical_key": "file:<normalized_path>",
  "source_path": "<normalized_path>"
}
```

**Field-level guarantees**:

- `id` is computed as `entity_id(canonical_key)` where `entity_id` is `auditgraph.storage.hashing.entity_id`. The same function is used by `auditgraph/git/materializer.py:build_links()` to derive `modifies` link `to_id` values, which is the contractual binding that makes this fix work.
- `type` is the literal string `"file"`. Not `"git:file"`, not `"code:file"`. Same as the pre-change `extract_code_symbols` output.
- `name` is the basename of the file path (the part after the last `/`, or the whole path if no `/` is present).
- `canonical_key` is the literal string `"file:"` followed by the normalized path. Path normalization uses `auditgraph.normalize.paths.normalize_path()`, the same normalizer the pre-change code used.
- `source_path` is the normalized path (without the `file:` prefix). Identical to the pre-change `extract_code_symbols` field.

**Forbidden fields** (would violate clarification Q1's "schema match exactly" decision):

- `path` (a renamed version of `source_path` — would break tests that read `source_path`)
- `kind` (a discriminator for symlink vs. regular file vs. submodule — clarification Q2 commits to uniform treatment, no kind tagging)
- `provenance` (an audit trail of which stage created the entity — would be additive but is explicitly out of scope per Q1's "match existing schema exactly")
- Any other field not listed above.

### Links written (no change to types or schemas, dangling references resolved)

The stage continues to write all existing link types to `pkg_root/links/<shard>/<link_id>.json`:

| Link Type | from → to | Pre-change behavior | Post-change behavior |
|-----------|-----------|---------------------|----------------------|
| `modifies` | commit → file | `to_id` computed but target entity often missing | `to_id` always resolves to a real file entity |
| `parent_of` | child commit → parent commit | Resolves | Resolves |
| `authored_by` | commit → author_identity | Resolves | Resolves |
| `contains` | repository → commit | Resolves | Resolves |
| `tags` | tag → commit | Resolves | Resolves |
| `on_branch` | head commit → ref | Resolves | Resolves |
| `succeeded_from` | new file → old file | One or both endpoints often dangling | Both endpoints resolve |

### Manifest written (one new field)

The stage manifest at `pkg_root/runs/<run_id>/git-provenance-manifest.json` MUST include file entity IDs in the `outputs_hash` calculation. The hash input becomes:

```json
{
  "entities": ["<sorted entity IDs from commit_nodes + author_nodes + tag_nodes + ref_nodes + [repo_node] + file_nodes>"],
  "links": ["<sorted link IDs as before>"]
}
```

The `artifacts` list MUST include the file entity paths alongside the existing entries.

### Reverse index written (unchanged)

`pkg_root/indexes/git-provenance/file-commits.json` continues to be written with the same structure: `{file_entity_id: [commit_id, ...]}`. The reverse index already used file entity IDs as keys; with this spec, those IDs now resolve to real on-disk entity files.

## Determinism

- The output of `build_file_nodes` is sorted by entity ID before being merged into `all_entities`.
- The combined `all_entities` list maintains the existing ordering convention: commits, authors, tags, refs, repo, then files (file entities last to keep the existing 5-type list contiguous).
- Two runs of `run_git_provenance` on the same workspace produce byte-identical entity files, byte-identical link files, byte-identical reverse index, and byte-identical stage manifest.

## Error handling (unchanged)

| Condition | Result |
|-----------|--------|
| `git_provenance.enabled == false` | `StageResult(status="skipped", detail={"reason": "disabled"})` |
| Missing `run_id` or upstream manifest | `StageResult(status="missing_manifest", detail={"run_id": ...})` |
| Git repository not found at `root` | `StageResult(status="error", detail={"error": "...", "root": ...})` |
| Otherwise | `StageResult(status="ok", detail={"manifest": ..., "profile": ..., "run_id": ...})` |

## Performance contract

- The new `build_file_nodes` step adds at most O(N) time for N = total file entries across all selected commits' `files_changed` lists, dominated by set insertion and a final sort.
- On the auditgraph dogfood corpus (~118 commits, ~140 distinct paths), the added overhead is well under 100 ms — negligible compared to the multi-second commit walk.
- File entity disk writes scale linearly with distinct path count. On a corpus with 10,000 distinct paths, this adds ~10,000 small JSON file writes to the existing entity write loop. Acceptable.

## Stability promises

- This contract is binding from the day this spec is merged.
- Future changes that add fields to file entities are non-breaking (additive).
- Future changes that remove or rename fields are breaking and require their own spec.
- The `entity_id(f"file:{path}")` ID derivation is a stable contract — changing it would invalidate every existing `modifies` link, every `succeeded_from` link, and every entry in `file-commits.json` reverse index. Treat as immutable.

## Test contract

The contract is enforced by the following tests in `tests/test_git_provenance_file_entities.py`:

| Test | Asserts |
|------|---------|
| `test_build_file_nodes_creates_one_entity_per_distinct_path` | Entity count = distinct path count |
| `test_build_file_nodes_dedupes_paths_across_commits` | Path touched N times → 1 entity |
| `test_build_file_nodes_entity_id_matches_modifies_link_target` | The ID of an entity for path `X` equals `entity_id(f"file:{X}")`, which is what `build_links` uses for `modifies` links to that path |
| `test_build_file_nodes_entity_has_required_fields` | Entity has exactly `id`, `type`, `name`, `canonical_key`, `source_path` and no extras |
| `test_build_file_nodes_is_deterministic` | Two calls with the same input produce identical output (including ordering) |
| `test_build_file_nodes_handles_empty_commit_list` | Returns `[]` not error |
| `test_build_file_nodes_handles_paths_with_no_directory` | `name` equals `path` for top-level files |
| `test_run_git_provenance_writes_file_entities_to_sharded_storage` | After full stage run, file entity files exist on disk in the right shard directories |
| `test_run_git_provenance_includes_file_entities_in_outputs_hash` | The stage manifest's outputs_hash changes when file entities change (replay safety) |
| `test_modifies_link_targets_resolve_to_real_entities_after_run_git_provenance` | For every `modifies` link in `pkg_root/links/`, the target entity exists on disk (the load-bearing US1 acceptance test) |
