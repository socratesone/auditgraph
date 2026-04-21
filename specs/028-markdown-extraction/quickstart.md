# Quickstart: Verify Spec-028 end-to-end

**Audience**: developer landing the spec, or reviewer sanity-checking the implementation.
**Goal**: Prove all six user stories work against a real workspace without reading test code.

This quickstart takes ≈5 minutes on a developer machine. Every command can be copied and pasted without editing. If any step produces unexpected output, stop and file a follow-up — do not ship.

## Prereqs

- `python3 --version` → 3.10 or higher
- This branch (`028-markdown-extraction`) checked out
- `make dev` has been run in the repo root
- A scratch directory outside the repo: `mkdir -p /tmp/spec028-scratch && cd /tmp/spec028-scratch`
- `jq` available on PATH for JSON filtering

## 1. Initialize and ingest a fresh markdown corpus (US1, US2, US4)

Files live under `notes/` because the default `include_paths` in the shipped `config/pkg.yaml` are `notes / repos / auditgraph / docs`. Putting files at the scratch root would mean they're outside every include path and `auditgraph run` would process zero files.

```bash
# Initialize — this creates config/pkg.yaml + the two shipped rule-pack stubs
auditgraph init --root .

# Create a notes/ directory and put markdown files there (default include_paths contains "notes")
mkdir -p notes
cat > notes/intro.md <<'MD'
# Introduction

Welcome to the demo. We use `PostgreSQL` and `Redis` for storage.

## Install

```bash
pip install auditgraph
```

See [the setup guide](setup.md) for details or visit
<https://example.com/docs>.
MD

cat > notes/setup.md <<'MD'
# Setup

## Prerequisites

- `PostgreSQL` 16 or later
- `postgresql-client` CLI tools
- A JSON file with config

See also [the intro](intro.md) and [the missing doc](ghost.md).
MD

# Full pipeline
auditgraph run
```

**Expected**:
- `auditgraph init` succeeds. The generated workspace contains:
  - `config/pkg.yaml`
  - `config/extractors/core.yaml` (shipped stub)
  - `config/link_rules/core.yaml` (shipped stub)
  — all three present, matching the package-resource stubs byte-identically (**US4** — no orphan references).
- `auditgraph run` completes with status `ok` at every stage. No `RulePackError`.
- Counts in the final JSON: `ingest.ok >= 2`, `extract` produced entities > 0.

## 2. Verify markdown sub-entities exist (US2)

```bash
auditgraph list --type ag:section    | jq '.results | length'
auditgraph list --type ag:technology | jq '.results | length'
auditgraph list --type ag:reference  | jq '.results | length'
```

**Expected counts** (exact):

- `ag:section`: **4** — `Introduction`, `Install`, `Setup`, `Prerequisites`.
- `ag:technology`: **5** — per-document dedup, so the same token in two documents produces two entities:
  - notes/intro.md: `postgresql`, `redis`, `bash` (the fence `info` string for the code block per FR-016g).
  - notes/setup.md: `postgresql`, `postgresql-client`.
  - 3 + 2 = 5 total. `postgresql-client` stays distinct from `postgresql` because case-fold does not strip `-client`.
- `ag:reference`: **4** — one per link across both files:
  - notes/intro.md: `setup.md` → `resolution="internal"`, `target_document_id` set.
  - notes/intro.md: `https://example.com/docs` (autolink) → `resolution="external"`.
  - notes/setup.md: `intro.md` → `resolution="internal"`.
  - notes/setup.md: `ghost.md` → `resolution="unresolved"`.

Check link topology via the `rule_id` field on each link record (links do NOT carry `from_type` / `to_type` — only `from_id`, `to_id`, `type`, `rule_id`):

```bash
# Count links by rule_id
find .pkg/profiles/default/links -name "lnk_*.json" \
  | xargs -I {} jq -r '.rule_id' {} \
  | sort | uniq -c
```

**Expected**: four rule_ids with positive counts:
- `link.markdown.contains_section.v1` — at least 4 (one per section; topmost headings hang off the note entity).
- `link.markdown.mentions_technology.v1` — up to 5 per-section edges (section-to-technology).
- `link.markdown.references.v1` — exactly 4 (one per `ag:reference`).
- `link.markdown.resolves_to_document.v1` — exactly 2 (only the two internal references).

Counts are lower-bounded rather than exact for `contains_section` and `mentions_technology` because they depend on where the markdown walker attaches section-to-technology edges (a decision the implementation may refine).

## 3. Verify determinism (US2, US1)

Extract and compare only the `outputs_hash` field — the manifest file itself will differ across runs because `wall_clock_*` fields change (US6).

```bash
jq -r '.outputs_hash' .pkg/profiles/default/runs/*/extract-manifest.json | sort -u > /tmp/spec028-outputs-before.txt

auditgraph run

jq -r '.outputs_hash' .pkg/profiles/default/runs/*/extract-manifest.json | sort -u > /tmp/spec028-outputs-after.txt

diff /tmp/spec028-outputs-before.txt /tmp/spec028-outputs-after.txt
```

**Expected**: `diff` emits nothing. `outputs_hash` is byte-identical across runs even though `wall_clock_started_at` / `wall_clock_finished_at` change.

## 4. Verify cache reuse preserves entities (US1)

```bash
# Edit an unrelated file outside include_paths so ingest has to inspect but not reprocess
touch unrelated.txt

# Rerun — the cache path kicks in for the two markdown files
auditgraph run

# Entity count should be the same, not 0
auditgraph list --count | jq '.count'
```

**Expected**: Entity count is equal to the previous run. Check the latest `ingest-manifest.json`: cached records for `notes/intro.md` and `notes/setup.md` carry `parse_status: "ok"`, `source_origin: "cached"`, `skip_reason: "unchanged_source_hash"`. Extract still emits entities from them.

## 5. Verify empty-pipeline warnings (US3)

The empty-pipeline demo uses a `.txt` source: only markdown sources emit a `note` entity, so a `.txt` corpus with no other extractors active produces zero entities and triggers the `no_entities_produced` warning.

```bash
mkdir -p empty-demo && cd empty-demo
auditgraph init --root .

# Override the generated config to allow only .txt and point at the current dir
cat > config/pkg.yaml <<'MD'
pkg_root: "."
active_profile: "default"
profiles:
  default:
    include_paths: ["."]
    exclude_globs: []
    ingestion:
      allowed_extensions: [".txt"]
    extraction:
      rule_packs: []
      ner:
        enabled: false
      markdown:
        enabled: false
    linking:
      rule_packs: []
MD

echo "hello world" > trivial.txt
auditgraph run
```

**Expected**: The final `extract` stage JSON contains a non-empty `detail.warnings` array:

```json
{"code": "no_entities_produced", "message": "extract produced 0 entities from 1 ingested file(s)", "hint": "..."}
```

Exit code is still `0` (warnings, not errors, per FR-019). The same warning appears in `.pkg/profiles/default/runs/<latest>/extract-manifest.json` at the top-level `warnings` field.

Return to the main scratch dir:

```bash
cd /tmp/spec028-scratch
```

## 6. Verify `auditgraph node` resolves every entity class (US5)

Documents aren't promoted to entity-index status (per R6). Grab a `doc_…` ID directly from the filesystem. Response shape uses the `results` key (not `items`).

```bash
DOC_ID=$(basename "$(ls .pkg/profiles/default/documents/doc_*.json | head -1)" .json)
ENT_ID=$(auditgraph list --type ag:section --limit 1 | jq -r '.results[0].id')
CHK_ID=$(basename "$(ls .pkg/profiles/default/chunks/*/chk_*.json | head -1)" .json)

auditgraph node "$DOC_ID"                     # expect: document view
auditgraph node "$ENT_ID"                     # expect: ag:section view
auditgraph node "$CHK_ID"                     # expect: chunk view
auditgraph node doc_deadbeef1234567890abcdef  # expect: structured not-found
```

**Expected**:
- First three return structured views.
- Fourth returns `{"status": "error", "code": "not_found", "message": "..."}` — not an OS `FileNotFoundError`.

## 7. Verify wall-clock timestamps in manifests (US6)

```bash
cat .pkg/profiles/default/runs/*/ingest-manifest.json \
  | jq '{started_at, wall_clock_started_at, wall_clock_finished_at}'
```

**Expected**:
- `started_at` is a deterministic ISO-8601 derived from the run_id hash (NOT current time — preserves cross-run byte identity of non-wall-clock manifest fields).
- `wall_clock_started_at` and `wall_clock_finished_at` are current UTC timestamps, within 60 seconds of now (typically within seconds — see SC-008).

## 8. Verify a misconfigured rule-pack is rejected (US4 edge case)

The CLI reads `<root>/config/pkg.yaml` by default — breaking the config here is what actually tests the validator. Because `auditgraph init` is intentionally idempotent (it does NOT overwrite an existing `config/pkg.yaml`), we save the known-good config first and restore it inline after the negative test rather than rerunning `init`.

```bash
# Save the known-good config so we can restore it after the negative test
cp config/pkg.yaml config/pkg.yaml.bak

# Overwrite the real config file with a broken rule_packs path
cat > config/pkg.yaml <<'MD'
pkg_root: "."
active_profile: "default"
profiles:
  default:
    include_paths: ["notes"]
    exclude_globs: []
    extraction:
      rule_packs: ["config/extractors/missing.yaml"]
MD

auditgraph run
echo "exit: $?"
```

**Expected**:
- Non-zero exit code (5).
- Structured JSON error naming the missing path: `{"status": "error", "code": "rule_pack_missing", "path": "config/extractors/missing.yaml", ...}`.
- Pipeline did not silently proceed.

Path resolution sanity check (no doubling, per FR-016f / adjustments2.md §4): the error message's `path` field shows `config/extractors/missing.yaml` resolved against the workspace root → `<scratch>/config/extractors/missing.yaml`, NOT `<scratch>/config/config/extractors/missing.yaml`.

Restore the valid config:

```bash
mv config/pkg.yaml.bak config/pkg.yaml
```

`auditgraph init` will NOT restore an overwritten config (it's idempotent — it checks `not target.exists()` before writing). The `mv` above is the deterministic way to get back to a working state.

## 9. Verify stale-entity pruning (US2 × FR-016c)

Edit a heading in one file and confirm the pre-edit section entity is gone on the next run.

```bash
SECTIONS_BEFORE=$(auditgraph list --type ag:section \
  | jq '[.results[] | select(.refs[0].source_path == "notes/intro.md")] | length')

# Rename "Install" → "Installation"
sed -i 's/^## Install$/## Installation/' notes/intro.md

auditgraph run

SECTIONS_AFTER=$(auditgraph list --type ag:section \
  | jq '[.results[] | select(.refs[0].source_path == "notes/intro.md")] | length')

echo "before: $SECTIONS_BEFORE  after: $SECTIONS_AFTER"
```

**Expected**: `SECTIONS_AFTER == SECTIONS_BEFORE`. No orphan "Install" section survives from the pre-edit run.

## 10. Verify cooccurrence exclusion (FR-016e)

Links carry `from_id`, `to_id`, `type`, `rule_id` — NOT `from_type` / `to_type`. FR-016e says markdown sub-entities are EXCLUDED from source-level cooccurrence entirely: a cooccurrence link MUST NOT have a markdown sub-entity on EITHER endpoint (not just both). To verify, we look up each endpoint's entity record and check its type, flagging any link where at least one endpoint is in the markdown type set.

```bash
python3 - <<'PY'
import json
from pathlib import Path

pkg = Path(".pkg/profiles/default")
markdown_types = {"ag:section", "ag:technology", "ag:reference"}

# Index every entity id -> type once (cheap on a demo corpus)
id_to_type = {}
for entity_file in pkg.glob("entities/*/ent_*.json"):
    rec = json.loads(entity_file.read_text())
    id_to_type[rec["id"]] = rec.get("type", "")

violations = 0
for link_file in pkg.glob("links/*/lnk_*.json"):
    link = json.loads(link_file.read_text())
    if link.get("rule_id") != "link.source_cooccurrence.v1":
        continue
    ftype = id_to_type.get(link.get("from_id", ""), "")
    ttype = id_to_type.get(link.get("to_id", ""), "")
    # FR-016e: EITHER endpoint being a markdown sub-entity is a violation
    if ftype in markdown_types or ttype in markdown_types:
        violations += 1
        print(f"VIOLATION: {link_file.name}: {ftype} -> {ttype}")

print(f"violations: {violations}")
PY
```

**Expected**: `violations: 0`. No `link.source_cooccurrence.v1` edge has a markdown sub-entity on either endpoint.

## 11. Clean up

```bash
cd /
rm -rf /tmp/spec028-scratch
```

---

## Acceptance checklist

Each numbered step below maps to the user stories in `spec.md`:

- [ ] Step 1: fresh init + run succeeds; init copies pkg.yaml AND both rule-pack stubs; files placed under `notes/` are ingested. **(US4)**
- [ ] Step 2: exact counts — 4 sections, 5 technologies, 4 references. Four markdown rule_ids all have positive link counts. **(US2)**
- [ ] Step 3: `outputs_hash` field is byte-identical across runs even though full manifest files differ. **(US2, US6)**
- [ ] Step 4: rerun after editing an unrelated file keeps all entities (cache hit path). **(US1)**
- [ ] Step 5: `.txt`-only corpus with markdown disabled surfaces `no_entities_produced` warning in JSON output and persisted manifest; exit code 0. **(US3)**
- [ ] Step 6: `auditgraph node` resolves doc/chunk/entity IDs via `.results[0]` lookup; unknown ID returns structured not-found. **(US5)**
- [ ] Step 7: `wall_clock_*` fields are real; `started_at` stays deterministic. **(US6)**
- [ ] Step 8: misconfigured rule-pack path (overwritten `config/pkg.yaml`) produces exit 5 and structured error; no `config/config/...` path doubling. **(US4, FR-016f)**
- [ ] Step 9: heading edit does not leave an orphan section entity. **(US2, FR-016c)**
- [ ] Step 10: no `link.source_cooccurrence.v1` link has both endpoints in the markdown sub-entity type set. **(US2, FR-016e)**

If all boxes check, Spec-028 is functionally complete. Run `pytest tests/test_spec028_*.py -v` for the regression-guard layer.
