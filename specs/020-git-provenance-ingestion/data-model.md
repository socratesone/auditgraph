# Data Model: Git Provenance Ingestion

**Feature**: 020-git-provenance-ingestion
**Date**: 2026-04-02

## Node Types

### Repository

| Field | Type | Description |
|-------|------|-------------|
| `id` | `repo_{sha256_text(canonical_key)}` | Full hex digest, deterministic from workspace root absolute path |
| `type` | `"repository"` | Node type discriminator |
| `name` | `string` | Repository directory name |
| `path` | `string` | Workspace root absolute path (used as canonical key for ID stability across moves) |

### Commit

| Field | Type | Description |
|-------|------|-------------|
| `id` | `commit_{sha256_text(canonical_key)}` | Full hex digest, deterministic from repo_path + ":" + commit_hex |
| `type` | `"commit"` | Node type discriminator |
| `sha` | `string` | Full 40-char hex commit hash |
| `subject` | `string` | First line of commit message |
| `author_name` | `string` | Author name |
| `author_email` | `string` | Author email |
| `authored_at` | `string` | ISO-8601 authored timestamp |
| `committer_name` | `string \| null` | Committer name (null if same as author) |
| `committer_email` | `string \| null` | Committer email (null if same as author) |
| `committed_at` | `string \| null` | ISO-8601 committed timestamp (null if same as authored_at) |
| `is_merge` | `boolean` | True if commit has >1 parent |
| `parent_shas` | `list[string]` | Parent commit hex hashes |
| `tier` | `"structural" \| "scored"` | Whether Tier 1 (anchor) or Tier 2 (budget) |
| `importance_score` | `float` | Tier 2 selection score; `-1.0` sentinel for Tier 1 (sorts above all Tier 2 scores) |

### AuthorIdentity

| Field | Type | Description |
|-------|------|-------------|
| `id` | `author_{sha256_text(canonical_key)}` | Full hex digest, deterministic from repo_path + ":" + email |
| `type` | `"author_identity"` | Node type discriminator |
| `email` | `string` | Canonical identity key |
| `name_aliases` | `list[string]` | All observed name variants, sorted for determinism |

### Tag

| Field | Type | Description |
|-------|------|-------------|
| `id` | `tag_{sha256_text(canonical_key)}` | Full hex digest, deterministic from repo_path + ":" + tag_name |
| `type` | `"tag"` | Node type discriminator |
| `name` | `string` | Tag name (e.g., `v1.2.0`) |
| `tag_type` | `"lightweight" \| "annotated"` | Tag kind |
| `target_sha` | `string` | Commit hex this tag points to |
| `tagger_name` | `string \| null` | Tagger name (annotated only) |
| `tagger_email` | `string \| null` | Tagger email (annotated only) |
| `tagged_at` | `string \| null` | ISO-8601 tag timestamp (annotated only) |

### Ref (Branch)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `ref_{sha256_text(canonical_key)}` | Full hex digest, deterministic from repo_path + ":" + ref_name |
| `type` | `"ref"` | Node type discriminator |
| `name` | `string` | Ref short name (e.g., `main`, `feature/auth`) |
| `ref_type` | `"branch" \| "remote"` | Local or remote tracking branch |
| `head_sha` | `string` | HEAD commit hash for this ref at ingestion time |

**Determinism**: All branch `head_sha` values are included in the stage's `inputs_hash` calculation. When any branch advances, `inputs_hash` changes, producing a new `run_id`. This ensures output is deterministic for any given `run_id` — the same `run_id` always produces the same Ref nodes with the same `head_sha` values.

### File (existing entity — not created by this stage)

Git provenance links to existing `ent_*` file entities produced by `run_ingest`. No new File nodes are created. Lookup MUST use `entity_id()` from `auditgraph/storage/hashing.py` directly — never reimplement the formula. The existing function returns `ent_{sha256_text(canonical_key)}` (full 64-char hex digest, no truncation).

---

## Relationship Types

### Commit TOUCHES File

```json
{
  "id": "lnk_{sha256(rule_id + ':' + commit_id + ':' + file_entity_id)}",
  "from_id": "commit_...",
  "to_id": "ent_...",
  "type": "modifies",
  "rule_id": "link.git_modifies.v1",
  "confidence": 1.0,
  "authority": "authoritative",
  "evidence": [{"commit_sha": "abc123", "source_path": "relative/path"}]
}
```

### Commit HAS_PARENT Commit

```json
{
  "id": "lnk_{sha256(rule_id + ':' + child_id + ':' + parent_id)}",
  "from_id": "commit_... (child)",
  "to_id": "commit_... (parent)",
  "type": "parent_of",
  "rule_id": "link.git_parent.v1",
  "confidence": 1.0,
  "authority": "authoritative",
  "evidence": [{"child_sha": "...", "parent_sha": "..."}]
}
```

### Commit AUTHORED_BY AuthorIdentity

```json
{
  "id": "lnk_{sha256(rule_id + ':' + commit_id + ':' + author_id)}",
  "from_id": "commit_...",
  "to_id": "author_...",
  "type": "authored_by",
  "rule_id": "link.git_authored_by.v1",
  "confidence": 1.0,
  "authority": "authoritative",
  "evidence": [{"commit_sha": "...", "author_email": "..."}]
}
```

### Repository CONTAINS Commit

```json
{
  "id": "lnk_{sha256(rule_id + ':' + repo_id + ':' + commit_id)}",
  "from_id": "repo_...",
  "to_id": "commit_...",
  "type": "contains",
  "rule_id": "link.git_contains.v1",
  "confidence": 1.0,
  "authority": "authoritative"
}
```

### Tag POINTS_TO Commit

```json
{
  "id": "lnk_{sha256(rule_id + ':' + tag_id + ':' + commit_id)}",
  "from_id": "tag_...",
  "to_id": "commit_...",
  "type": "tags",
  "rule_id": "link.git_tags.v1",
  "confidence": 1.0,
  "authority": "authoritative"
}
```

### File SUCCEEDED_FROM File (lineage)

```json
{
  "id": "lnk_{sha256(rule_id + ':' + new_file_id + ':' + old_file_id)}",
  "from_id": "ent_... (new path)",
  "to_id": "ent_... (old path)",
  "type": "succeeded_from",
  "rule_id": "link.git_lineage.v1",
  "confidence": 1.0 | 0.8 | 0.6,
  "authority": "heuristic",
  "evidence": [{"commit_sha": "...", "old_path": "...", "new_path": "...", "detection_method": "rename|similarity|basename_match"}]
}
```

---

## Storage Layout

Git provenance artifacts follow the existing `shard_dir()` convention. Shard directories are **dynamically assigned** based on the first two hex characters of the hash portion of the ID (everything after the first `_`). For example, `commit_a3b4c5...` shards to `entities/a3/commit_a3b4c5....json`.

Entities MUST be written using `shard_dir(pkg_root / "entities", entity_id)` to ensure `load_entity()` can locate them by ID. Links MUST use `shard_dir(pkg_root / "links", link_id)`.

```
.pkg/profiles/default/
├── entities/
│   └── {2-hex-char}/    # dynamic shard dirs (a3/, f1/, etc.)
│       ├── commit_*.json
│       ├── author_*.json
│       ├── repo_*.json
│       └── tag_*.json
├── links/
│   └── {2-hex-char}/    # dynamic shard dirs, same as existing links
│       └── lnk_*.json
├── indexes/
│   └── git-provenance/
│       └── file-commits.json   # reverse index: file_entity_id → [commit_ids]
└── runs/
    └── {run_id}/
        ├── git-provenance-manifest.json
        └── replay-log.jsonl  (appended)
```

### Reverse Index for Queries

The materializer writes a reverse adjacency index at `indexes/git-provenance/file-commits.json` mapping each file entity ID to its list of commit entity IDs. This enables O(1) lookup for `git-who`, `git-log`, and `git-introduced` queries without requiring a full link directory scan.

---

## Config Schema

Config lives inside the profile dict (accessed via `config.profile().get("git_provenance", {})`), consistent with other pipeline-stage settings like `ingestion`, `extraction`, etc.

```yaml
# Inside profiles.default (or any named profile):
profiles:
  default:
    git_provenance:
      enabled: false                     # default: false — opt-in per profile
      max_tier2_commits: 1000            # Tier 2 budget (Tier 1 is unbounded)
      hot_paths: []                      # glob patterns promoting commits to Tier 1
      cold_paths:                        # glob patterns scoring 0 in Tier 2
        - "*.lock"
        - "*-lock.json"
        - "*.generated.*"
```

Note: `lineage_similarity_threshold` is fixed at 70% in v1 (not configurable). See research.md.
