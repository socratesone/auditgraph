# Contract: `StageManifest.warnings` + wall-clock timestamps

**Modules**:
- `auditgraph/storage/manifests.py` — dataclass definitions.
- `auditgraph/pipeline/warnings.py` — NEW helper module.
- `auditgraph/pipeline/runner.py :: _write_stage_manifest` and each `run_*` method — producers.
- `auditgraph/cli.py :: _emit` — surfacing to CLI output.

## `StageManifest` extended fields

```python
@dataclass(frozen=True)
class StageManifest:
    # ... existing fields (version, schema_version, stage, run_id, ...
    #     started_at, finished_at, inputs_hash, outputs_hash, config_hash,
    #     status, artifacts) ...
    wall_clock_started_at: str | None = None
    wall_clock_finished_at: str | None = None
    warnings: list[dict[str, str]] = field(default_factory=list)
```

`IngestManifest` gains the same three fields with identical semantics.

## Invariants

- Neither `wall_clock_*` nor `warnings` participates in `outputs_hash` (invariant I7).
- Empty `warnings` list on a manifest is semantically identical to "no warnings." Consumers MUST handle absence and empty list identically.
- Order of entries in `warnings` is insertion order. Stable across reruns only if the underlying condition is stable (the field is for advisory UX, not hash input).

## `auditgraph/pipeline/warnings.py` public API

```python
THROUGHPUT_WARNING_NO_ENTITIES = "no_entities_produced"
THROUGHPUT_WARNING_EMPTY_INDEX = "empty_index"

@dataclass(frozen=True)
class ThroughputWarning:
    code: str
    message: str
    hint: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "hint": self.hint}

def warning_no_entities(upstream_inputs: int) -> ThroughputWarning:
    """Return a zero-entities warning sized to the upstream input count."""

def warning_empty_index(entity_count: int) -> ThroughputWarning:
    """Return an empty-index warning sized to the on-disk entity count."""
```

Message/hint copy (authoritative):

- `no_entities_produced`:
  - message: `f"extract produced 0 entities from {upstream_inputs} ingested file(s)"`
  - hint: `"Check that at least one extractor is active for the ingested file types. For markdown corpora, verify the markdown sub-entity producer is enabled."`
- `empty_index`:
  - message: `f"index is empty despite {entity_count} entities on disk"`
  - hint: `"Re-run 'auditgraph rebuild' from a clean state, or inspect 'indexes/bm25/index.json' for corruption."`

## Producer wiring

### `run_extract` (`runner.py:554`)

Immediately after the entity list is finalized (around current line 628), compute:

```python
upstream_ok = sum(
    1 for record in normalized_records
    if record.get("parse_status") == "ok"
)
warnings: list[dict[str, str]] = []
if upstream_ok >= 1 and len(entity_list) == 0:
    warnings.append(warning_no_entities(upstream_ok).to_dict())
```

Pass `warnings` through to `_write_stage_manifest` as an additional kwarg; include it in the returned `StageResult.detail`.

### `run_index` (same pattern)

- After BM25 index is built, if `entities_on_disk >= 1` and `bm25_entries == 0`, emit `warning_empty_index`.

### `_write_stage_manifest`

```python
def _write_stage_manifest(
    self,
    pkg_root: Path,
    stage: str,
    run_id: str,
    inputs_hash: str,
    outputs_hash: str,
    config_hash: str,
    artifacts: list[str],
    status: str = "ok",
    warnings: list[dict[str, str]] | None = None,
    wall_clock_started_at: str | None = None,
    wall_clock_finished_at: str | None = None,
) -> Path:
    ...
```

## `wall_clock_now()` helper

```python
# in auditgraph/storage/hashing.py (colocated with deterministic_timestamp)

def wall_clock_now() -> str:
    """Return the current UTC wall-clock time as ISO-8601."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- Monkeypatchable in tests via `monkeypatch.setattr("auditgraph.storage.hashing.wall_clock_now", lambda: "2026-04-20T10:00:00Z")`.
- Never participates in any hash. Used only to fill `wall_clock_*` fields.

## Canonical warning locations (authoritative, fixes adjustments3.md §8)

Warnings appear in exactly two places. The serialization rules are asymmetric on purpose — live results optimise for brevity, persisted manifests optimise for a stable key operators can consume.

**1. Live stage result** (returned from `run_extract` / `run_index` / etc.):

```python
StageResult(
    stage="extract",
    status="ok",
    detail={
        # ...existing detail fields (counts, manifest path, profile, etc.)...
        "warnings": [
            {"code": "no_entities_produced", "message": "...", "hint": "..."},
        ],
    },
)
```

Rule: the `warnings` key lives under `StageResult.detail`. When there are no warnings, the key MAY be omitted (absence and empty list are semantically equivalent). Tests MUST treat both shapes identically.

**2. Persisted stage manifest** (on disk at `runs/<run_id>/<stage>-manifest.json`):

```json
{
  "version": "v1",
  "stage": "extract",
  "status": "ok",
  "...": "...",
  "warnings": []
}
```

Rule: the `warnings` key lives at the **top level** of the manifest JSON and is ALWAYS present — serialized as `[]` when empty, as a populated list when warnings exist. This gives operators, CI jobs, and the reviewer checklist a stable JSON path (`.warnings`) they can query regardless of whether the stage emitted any warnings.

Neither representation participates in `outputs_hash` (invariant I7). The asymmetry — live MAY omit, persisted MUST include — is intentional; do not "harmonize" by making persisted omit on empty.

## Copy rule (live → manifest)

The runner MUST copy `StageResult.detail["warnings"]` verbatim into the manifest's top-level `warnings` field before writing. No transformation, sorting, or filtering. Identical semantics, two locations.

## CLI surfacing (`cli.py :: _emit`)

The existing `_emit(payload)` function JSON-serializes a dict. The CLI handler (`auditgraph/cli.py :: main`) already emits `{"stage": ..., "status": ..., "detail": {...}}` for stage commands. When `detail["warnings"]` is non-empty, it is already in the emitted JSON via the `detail` pass-through. `_emit` does NOT transform the shape — it pretty-prints whatever dict it receives.

- JSON output mode (default): warnings are accessible at the JSON path `.detail.warnings` for stage commands and at `.warnings` when inspecting the persisted manifest file directly.
- Future non-JSON mode (out of scope here): would render a stderr-highlighted block.

Exit code remains `0` regardless of warnings (FR-019).

## Zero-warning fixture constraint

A test that asserts `warnings == []` (or absence) MUST use a source configuration that actually produces zero entities. A markdown file produces at minimum a `note` entity via `build_note_entity` — so a markdown-only fixture CANNOT be a zero-warning fixture. Either:

- Use `.txt` input (does not pass through the `if parser_id == "text/markdown"` branch that calls `build_note_entity`), OR
- Disable all extractors via config (`extraction.markdown.enabled: false`, `extraction.ner.enabled: false`, no ADR or log content) in addition to markdown, OR
- Use an ingested source that legitimately produces zero entities (e.g., a `.log` file whose regex rules match nothing).

The quickstart and T037's `test_one_entity_from_nonzero_input_emits_no_warning` both rely on this constraint.

## Test contract

- **Warning fires on zero output**: ingest 1 valid markdown file, disable the new markdown producer via config (simulating "all producers off"). Assert `run_extract` returns `StageResult` with `warnings[0]["code"] == "no_entities_produced"`. Assert the persisted `extract-manifest.json` has `warnings` with the same content.
- **Warning silent on happy path**: ingest 1 valid markdown file with producer enabled → `warnings == []` and no `warnings` key surfaces noise in the CLI output.
- **Empty-index warning**: construct a state with entities on disk but empty BM25 index (controlled fixture). Assert `run_index` emits `empty_index`.
- **Warnings do not affect `outputs_hash`**: run the pipeline twice against the same input, with and without simulated warning scenarios mixed in. `outputs_hash` is identical across runs.
- **Wall-clock fields are real**: after running a stage, assert `wall_clock_started_at` parses as ISO-8601 within 5s of the current time.
- **Wall-clock pinning in tests**: monkeypatch `wall_clock_now` to a fixed string; assert manifest carries that exact string. Used by determinism regression tests to keep manifests byte-identical across test runs.
