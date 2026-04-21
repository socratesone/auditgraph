# Contract: `IngestRecord` with orthogonal `source_origin`

**Modules**:
- `auditgraph/storage/manifests.py` — dataclass definition.
- `auditgraph/ingest/sources.py :: build_source_record` — producer (ingest stage).
- `auditgraph/ingest/manifest.py :: build_manifest` — aggregator (ingest stage).
- `auditgraph/pipeline/runner.py :: run_extract` — consumer (extract stage; also reads legacy shape).

## Producer contract

### `build_source_record` extended signature

```python
def build_source_record(
    path: Path,
    root: Path,
    parser_id: str,
    parse_status: str,
    status_reason: str | None = None,
    skip_reason: str | None = None,
    extra_metadata: dict[str, object] | None = None,
    *,
    source_origin: str = "fresh",   # NEW: "fresh" or "cached"
) -> tuple[IngestRecord, dict[str, object]]:
    ...
```

`source_origin` is keyword-only to avoid silent positional mix-ups with the existing `skip_reason` / `extra_metadata` tail.

### `run_ingest` call sites

- **Cache hit — complete record** (`runner.py:162-175` today): must set `parse_status="ok"`, `source_origin="cached"`, keep `skip_reason=SKIP_REASON_UNCHANGED` for observability. Downstream stages now admit this record. **Completeness check** (per FR-016b1): before taking this branch for a markdown source, verify the cached `documents/<doc_id>.json` payload contains the `text` field. If missing, fall through to the fresh-parse branch instead.
- **Cache hit — incomplete record (Spec-028 migration)**: when `existing_document_path.exists()` AND `source_hash` matches BUT the cached payload lacks a required field for the current parser (markdown: `text`), reparse the source as if there were no cache hit. Record the result as `parse_status="ok"`, `source_origin="fresh"` (NOT `cached`), and write the refreshed document payload over the incomplete one. No warning is emitted — this is an expected one-time migration.
- **Fresh parse success** (`runner.py:177-189`): `parse_status="ok"`, `source_origin="fresh"` (default).
- **Fresh parse failure** (`runner.py:183`): `parse_status="failed"`, `source_origin="fresh"`.
- **Unsupported extension** (`runner.py:209-219`): `parse_status="skipped"`, `source_origin="fresh"` (the file was seen this run; nothing was parsed).
- **Refused symlink** (`runner.py:221-233`): `parse_status="skipped"`, `source_origin="fresh"`.

### `IngestRecord` dataclass

```python
@dataclass(frozen=True)
class IngestRecord:
    path: str
    source_hash: str
    size: int
    mtime: float
    parser_id: str
    parse_status: str          # "ok" | "failed" | "skipped"
    status_reason: str | None = None
    skip_reason: str | None = None
    source_origin: str = "fresh"   # NEW: "fresh" | "cached"
```

Serialized JSON adds one field (`source_origin`). Deserialization tolerates absent field (defaults to `"fresh"`) for reading legacy pre-028 manifests.

## Consumer contract

### `_normalize_ingest_records(records)` helper

```python
def _normalize_ingest_records(
    records: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """
    Return a shallow copy of records with legacy cache-hit shape translated
    to the canonical spec-028 shape.

    Rule: any record with parse_status == "skipped" AND
    skip_reason in {"unchanged_source_hash", SKIP_REASON_UNCHANGED}
    becomes parse_status="ok", source_origin="cached".

    All other records are unchanged.
    """
```

- Called at the top of `run_extract` after loading the ingest manifest.
- Pure function — no disk writes. Does not mutate the on-disk manifest.
- Deterministic: same input list → same output list.

### Extract filter change

Both filter sites (`runner.py:567-571` list comprehension and `runner.py:576-578` for-loop continue) now reference the normalized record list. The condition `record.get("parse_status") != "ok"` stays verbatim — the fix is in what reaches the filter, not in the filter itself.

## Invariants (I6 from data-model.md)

- `parse_status ∈ {"ok", "failed", "skipped"}` — exhaustive.
- `source_origin ∈ {"fresh", "cached"}` — exhaustive.
- `parse_status == "failed"` → `source_origin == "fresh"` (cache never stores failures).
- `source_origin == "cached"` → `parse_status == "ok"` (cache is only populated from successful parses).
- `parse_status == "skipped"` → no constraint on `source_origin`; by convention the producer sets `"fresh"` because no parse was attempted.

## Test contract

- **Cache-hit produces ok/cached**: fixture with one markdown file, run ingest twice, assert second run's record has `parse_status="ok"`, `source_origin="cached"`, `skip_reason="unchanged_source_hash"`.
- **Cache-hit reaches extract**: after a cache-hit ingest, `run_extract` MUST produce entities for the cached file's content.
- **Fresh failure stays failed**: fixture with an unparseable file, assert `parse_status="failed"`, `source_origin="fresh"`, and the file is NOT emitted to extract.
- **Backward-compat reader**: handcrafted legacy ingest manifest with `parse_status="skipped"` + `skip_reason="unchanged_source_hash"`. Feed it to `run_extract`; assert entities are produced.
- **Backward-compat does not mutate disk**: after the backward-compat read, assert the on-disk `ingest-manifest.json` is unchanged (no silent migration).
- **Cached flag independence**: assert `parse_status == "failed" and source_origin == "cached"` is never constructed (unit test on `build_source_record`).
