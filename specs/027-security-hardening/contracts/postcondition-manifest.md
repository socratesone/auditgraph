# Contract: Redaction postcondition manifest field

Formalizes the `redaction_postcondition` field that `auditgraph rebuild` writes to its final run manifest. This field is the durable record of the postcondition's outcome, used by CI callers, the future `auditgraph diff` command, and human operators reading run reports.

Applies to: User Story 8 / FR-025 through FR-028 / Clarification Q2.

## Location

The field lives at the top level of the final-stage manifest produced by `run_rebuild` — by convention this is `.pkg/profiles/<profile>/runs/<run_id>/index-manifest.json` because `index` is the last stage in the rebuild pipeline. If the plan phase discovers a cleaner home (e.g., a dedicated `postcondition-manifest.json`), the field shape is unchanged — this contract is shape-first, not location-first.

The field is **absent** from stage manifests produced by standalone stages (`auditgraph ingest` alone, `auditgraph link` alone, etc.) because the postcondition only runs at the end of a full rebuild. Absence of the field in a partial-run manifest is not an error.

## Shape

```json
{
  "redaction_postcondition": {
    "status": "pass" | "fail" | "tolerated" | "skipped",
    "misses": [<Miss>, ...],
    "allow_misses": false | true,
    "scanned_shards": 12847,
    "wallclock_ms": 312
  }
}
```

## Status state machine

| Status | When emitted | `misses` | `allow_misses` | Exit code |
|---|---|---|---|---|
| `pass` | Postcondition ran and found zero matching strings across all scanned shards | `[]` | `false` | `0` |
| `fail` | Postcondition ran, found ≥ 1 match, and `--allow-redaction-misses` was NOT passed | `[<Miss>, ...]` (≥ 1 entry) | `false` | **`3`** (see `cli-commands.md`) |
| `tolerated` | Postcondition ran, found ≥ 1 match, and `--allow-redaction-misses` WAS passed | `[<Miss>, ...]` (≥ 1 entry) | `true` | `0` |
| `skipped` | Postcondition did not run because an earlier pipeline stage failed | `[]` | `false` | whatever exit code the prior stage produced |

A valid manifest satisfies the state machine constraints above. Validation rules (enforced by tests, not by a runtime schema guard):

- `status == "pass"` ⇒ `misses == []` and `allow_misses == false`.
- `status == "fail"` ⇒ `len(misses) >= 1` and `allow_misses == false`.
- `status == "tolerated"` ⇒ `len(misses) >= 1` and `allow_misses == true`.
- `status == "skipped"` ⇒ `misses == []`, `scanned_shards == 0`, `wallclock_ms == 0`.

## `Miss` sub-shape

Each entry in the `misses` array records one shard file that contained a detector-matched string:

```json
{
  "path": "chunks/ab/cd1234.json",
  "category": "credential",
  "field": "text"
}
```

### Field constraints

| Field | Type | Constraint |
|---|---|---|
| `path` | string | Relative path under `.pkg/profiles/<profile>/`, POSIX style with forward slashes. Deterministic (same file produces same string across platforms). |
| `category` | string | Detector category name from `redaction.py:_default_detectors()`. Post-Spec-027 valid values: `credential`, `jwt`, `bearer`, `url_credential`, `vendor_token`, `cloud_keys`, `pem_private_key`. Future detectors MUST use new category names, not rename existing ones. |
| `field` | string | Top-level string field in the shard JSON that held the match. Examples: `text`, `name`, `canonical_key`, `source_path`. Plan phase decides whether to descend into nested object fields. |

### What MUST NOT appear in a `Miss` entry

- **The matched secret value.** Recording the value in the manifest defeats the entire purpose of the redaction trust boundary — it re-persists the secret in the very file the operator is using to decide whether to panic. The `Miss` entry says "there's a secret at this location"; it never says "the secret is X".
- **Line numbers or byte offsets within the shard file.** These would help a human locate the match but add a deterministic-ordering burden and risk leaking information about the secret's position. Plan phase can add them later if needed.
- **The surrounding context** (the characters before and after the match). Same reason.

## Ordering determinism

The `misses` array MUST be sorted for deterministic output:
1. Primary key: `path` (lexicographic)
2. Tiebreaker: `field`
3. Tiebreaker: `category`

Identical inputs to the postcondition produce identical `misses` arrays. This matters for run-diff and CI regression tests.

## `scanned_shards` counting

- Count of shard JSON files actually walked by the postcondition. This is NOT the count of total files under `.pkg/`; files in `runs/`, `indexes/`, `secrets/` are excluded because the postcondition doesn't scan them (same scope rules as `validate-store` per Clarification Q5).
- Used to verify SC-008 (postcondition wallclock stays within budget relative to scanned shards).
- Zero on `status == "skipped"`.

## `wallclock_ms` measurement

- Integer milliseconds, measured from when the postcondition starts its walk to when the manifest entry is written.
- Does NOT include the time spent writing the manifest itself (to keep the measurement focused on the scan, not the I/O glue).
- Used by CI to assert SC-008: `wallclock_ms` of the postcondition is within 100% of the baseline rebuild wallclock on the reference test workspace.

## Example manifests

### Clean rebuild

```json
{
  "stage": "index",
  "status": "ok",
  "run_id": "run_abc123",
  "artifacts": ["..."],
  "redaction_postcondition": {
    "status": "pass",
    "misses": [],
    "allow_misses": false,
    "scanned_shards": 12847,
    "wallclock_ms": 287
  }
}
```

### Dirty rebuild (blocked)

```json
{
  "stage": "index",
  "status": "error",
  "run_id": "run_def456",
  "artifacts": ["..."],
  "redaction_postcondition": {
    "status": "fail",
    "misses": [
      {"path": "chunks/ab/cd1234.json", "category": "credential", "field": "text"},
      {"path": "chunks/ef/gh5678.json", "category": "cloud_keys", "field": "text"}
    ],
    "allow_misses": false,
    "scanned_shards": 12847,
    "wallclock_ms": 305
  }
}
```

(Process exited with code 3.)

### Dirty rebuild (tolerated)

```json
{
  "stage": "index",
  "status": "ok",
  "run_id": "run_def456",
  "artifacts": ["..."],
  "redaction_postcondition": {
    "status": "tolerated",
    "misses": [
      {"path": "chunks/ab/cd1234.json", "category": "credential", "field": "text"}
    ],
    "allow_misses": true,
    "scanned_shards": 12847,
    "wallclock_ms": 301
  }
}
```

(Process exited with code 0. The `allow_misses: true` is the auditable record that the operator chose to tolerate the miss.)

### Skipped (prior stage failed)

```json
{
  "stage": "extract",
  "status": "error",
  "run_id": "run_ghi789",
  "error": "extract stage failed",
  "redaction_postcondition": {
    "status": "skipped",
    "misses": [],
    "allow_misses": false,
    "scanned_shards": 0,
    "wallclock_ms": 0
  }
}
```

The `skipped` status is emitted so that run-diff tooling can tell "the postcondition didn't run" apart from "the postcondition passed" — the absence of the field would be ambiguous, so the `skipped` explicit state is preferred.

## Backwards compatibility

- Tools and tests that read pre-Spec-027 rebuild manifests handle the absence of `redaction_postcondition` gracefully. The field is additive.
- Tools that read Spec 027+ manifests SHOULD check for the field's presence before accessing it, but are not required to — a missing field can be safely treated as `{"status": "skipped", ...}` for display purposes.
- The field shape is stable: future detector categories add to the enum without renaming. If a future spec changes the `Miss` sub-shape, it MUST add fields rather than modifying existing ones.

## Relationship to `validate-store`

`auditgraph validate-store` produces an output shape that deliberately mirrors `redaction_postcondition` so tooling can consume both with the same logic. The only differences are:

- `validate-store` output is standalone (not embedded in a run manifest).
- `validate-store` supports `--all-profiles`, which wraps the postcondition shape in a `profiles: {<name>: ...}` dict.
- `validate-store` never produces `status: "skipped"` (it either runs or refuses to run at all).
- `validate-store` never produces `status: "tolerated"` (it has no opt-out flag; it's an audit tool, not a gate).

Valid statuses for `validate-store`: `"pass"`, `"fail"`. Valid for the postcondition: all four.
