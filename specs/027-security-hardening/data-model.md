# Phase 1 Data Model — Spec 027

Spec 027 introduces no new entity types in the auditgraph schema sense (no new shard directory, no new `type` value for stored entities, no schema version bump). What it introduces is:

1. A new manifest field on `rebuild` runs (`redaction_postcondition`).
2. A new skip-reason value in the existing ingest-manifest vocabulary.
3. A new detector category name alongside existing categories in the redaction summary.
4. A new structured error envelope returned by the MCP server on payload validation failure.

Each is documented below with field types, defaults, constraints, and example values. The contracts under `contracts/` formalize the interfaces that consume these shapes.

---

## 1. Run manifest: `redaction_postcondition` field

**Where it lives**: `.pkg/profiles/<profile>/runs/<run_id>/index-manifest.json` (or whichever manifest is written by the final stage of `run_rebuild` — plan-phase decides exact file; the shape is the same regardless). The field is added at the top level of the manifest.

**Introduced by**: FR-025, FR-026, FR-027.
**Consumed by**: `auditgraph rebuild` CLI exit-code logic; future `auditgraph diff` comparing two runs; human operators reading run reports.

### Field shape

```json
{
  "redaction_postcondition": {
    "status": "pass",
    "misses": [],
    "allow_misses": false,
    "scanned_shards": 12847,
    "wallclock_ms": 312
  }
}
```

### Field definitions

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `status` | enum `"pass" \| "fail" \| "tolerated" \| "skipped"` | Yes | — | Postcondition outcome. `pass` = no misses detected. `fail` = misses detected, run exited non-zero (exit code 3). `tolerated` = misses detected but `--allow-redaction-misses` was passed, run exited zero. `skipped` = postcondition did not run (e.g., early-exit from a prior stage failure). |
| `misses` | array of `Miss` (see below) | Yes | `[]` | One entry per shard file that contained a detector-matched string. Empty on `status: "pass"` or `status: "skipped"`. |
| `allow_misses` | boolean | Yes | `false` | Whether `--allow-redaction-misses` was passed on the command line. Only `true` when `status: "tolerated"`. Recorded even on pass/fail to make the CLI invocation fully auditable from the manifest alone. |
| `scanned_shards` | integer ≥ 0 | Yes | — | Count of shard files the postcondition actually walked. Zero on `skipped`. |
| `wallclock_ms` | integer ≥ 0 | Yes | — | Wall-clock time the postcondition took. Used to verify SC-008 (no more than doubling the baseline rebuild). |

### `Miss` sub-shape

```json
{
  "path": "chunks/ab/cd1234.json",
  "category": "credential",
  "field": "text"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | string | Yes | Relative path under `.pkg/profiles/<profile>/`. Forward slashes only, POSIX-style, deterministic. |
| `category` | string | Yes | Detector category name (e.g., `credential`, `cloud_keys`, `vendor_token`, `bearer`, `jwt`, `pem_private_key`, `url_credential`). Must match a category produced by `_default_detectors()`. |
| `field` | string | Yes | Which top-level string field in the shard JSON held the match (e.g., `text`, `name`, `canonical_key`). Enables a human reader to locate the issue without greping the file. |

**MUST NOT include**: the matched secret value. The postcondition's job is to say "there's a secret in this file"; echoing it into the manifest would defeat the purpose and reflect attacker input into operator logs.

### Validation rules

- `status == "pass"` ⇒ `misses == []` and `allow_misses == false`.
- `status == "fail"` ⇒ `len(misses) >= 1` and `allow_misses == false`; CLI exit code MUST be 3.
- `status == "tolerated"` ⇒ `len(misses) >= 1` and `allow_misses == true`; CLI exit code MUST be 0.
- `status == "skipped"` ⇒ `misses == []`, `scanned_shards == 0`, `wallclock_ms == 0`.

---

## 2. Ingest manifest: new `symlink_refused` skip reason

**Where it lives**: `.pkg/profiles/<profile>/runs/<run_id>/ingest-manifest.json`, in the `sources[].skip_reason` field for each refused path.

**Introduced by**: FR-001, FR-002, FR-004.

### Skip-reason vocabulary after Spec 027

| Value | Defined by | Meaning |
|---|---|---|
| `unchanged` | Existing (`SKIP_REASON_UNCHANGED`) | Source hash matches the existing document; no re-parse needed. |
| `unsupported_extension` | Existing (`SKIP_REASON_UNSUPPORTED`) | File extension not in the allowlist. |
| `excluded` | Existing | File matched an exclude glob. |
| `too_large` | Existing | File exceeded `max_file_size_bytes`. |
| **`symlink_refused`** | **NEW (Spec 027)** | Path is a symlink whose resolved real target falls outside the workspace root, OR the symlink target does not exist (broken symlink). The file is not read and its contents never enter the pipeline. |

### Constant

`auditgraph/ingest/policy.py` exports `SKIP_REASON_SYMLINK_REFUSED = "symlink_refused"` (new constant added by this spec).

### Stderr summary line format

In addition to the per-source manifest entry, a single summary line is written to stderr at the end of ingest when the refused count is ≥ 1:

```
WARN: refused 2 symlinks pointing outside /home/user/workspace (see manifest for details)
```

The format is stable: `WARN:` prefix, literal `refused N symlinks pointing outside <absolute_resolved_workspace_root>`, literal `(see manifest for details)`. The count is a plain integer; the path is the resolved absolute path. The line is emitted exactly once per run regardless of count.

---

## 3. Redaction detector categories

**Where it lives**: `auditgraph/utils/redaction.py:_default_detectors()` returns a dict where each entry's `category` string determines how matches are reported in `RedactionSummary`. The summary is embedded in various artifacts (source records, run manifests, Neo4j export metadata).

**Introduced by**: FR-012, FR-013, FR-014 (Clarification Q6).

### Category set after Spec 027

| Category | Detector(s) | Examples |
|---|---|---|
| `jwt` | `jwt` | `eyJhbGc...base64.base64` |
| `bearer` | `bearer_token` | `Authorization: Bearer abc.def.ghi` |
| `credential` | `credential_kv` (expanded) | `password=foo`, `secret: bar`, `api_key=xyz`, `aws_access_key_id=ABC` (NEW: `aws_access_key_id`, `aws_secret_access_key`, `auth_token`, `access_token`, `refresh_token`, `session_token`, `passwd`, `pwd`, `bearer`, `auth`) |
| `url_credential` | `url_credentials` | `https://user:password@host/` |
| `vendor_token` | `vendor_token` (narrowed) | `ghp_...`, `github_pat_...` (NEW), `gho_...` (NEW), `ghu_...` (NEW), `ghs_...` (NEW), `ghr_...` (NEW), `xox[baprs]-...`, `xoxe.xoxp-...` (NEW) |
| **`cloud_keys`** (**NEW**) | `cloud_keys` (one detector with alternation, or multiple sub-detectors sharing the category name — plan-phase decision) | `AKIAIOSFODNN7EXAMPLE` (AWS), `AIza...` (Google), `sk-ant-...` (Anthropic), `sk-proj-...` / `sk-...` (OpenAI), `sk_live_...` (Stripe) |
| `pem_private_key` | `pem_private_key` | `-----BEGIN ... PRIVATE KEY-----` ... `-----END ... PRIVATE KEY-----` |

### Contract

- **`vendor_token` stays narrow to GitHub and Slack developer platform tokens.** It does NOT match cloud IAM credentials even if a future format uses similar-looking prefixes. The narrow scope preserves the severity signal in summary reports.
- **`cloud_keys` is the IAM credential bucket.** Rotation workflow: cloud console, SDK re-auth, possibly cascading permission updates.
- **The two categories appear as independent entries** in `RedactionSummary.by_category`. Summary reports do not merge them.
- **Positive + negative tests are mandatory** for each new format (FR-015). The positive test asserts the detector matches; the negative test asserts a visually-similar benign string does not match.

### Example summary output

```json
{
  "redaction_summary": {
    "by_category": {
      "credential": 3,
      "cloud_keys": 2,
      "vendor_token": 1
    },
    "total": 6
  }
}
```

---

## 4. MCP validation error envelope

**Where it lives**: Returned by `llm-tooling/mcp/server.py:execute_tool` when `llm-tooling/mcp/validation.py:validate` rejects the payload. The envelope replaces the successful result dict.

**Introduced by**: FR-005, FR-008 (Clarification Q4).

### Envelope shape

```json
{
  "error": {
    "code": "validation_failed",
    "tool": "ag_query",
    "field": "/q",
    "reason": "expected string, got integer"
  }
}
```

### Field definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `error` | object | Yes | Top-level wrapper. Indicates this is an error response. |
| `error.code` | string constant | Yes | Always `"validation_failed"` for this error class. Distinct from other MCP error codes (`forbidden`, `timeout`, `subprocess_failed`, etc.). |
| `error.tool` | string | Yes | The tool name that was being invoked (e.g., `ag_query`, `ag_list`). Matches the `name` field in `tool.manifest.json`. |
| `error.field` | string (JSON Pointer) | Yes | Where in the payload the violation occurred, as a JSON Pointer (RFC 6901). `/q` means the top-level `q` key; `/filters/0/op` would mean the `op` field of the first element of the `filters` array. Empty string `""` means the whole payload. |
| `error.reason` | string | Yes | Human-readable description of the violation. MUST NOT include the rejected value to avoid reflecting attacker input. Examples: `"unknown property"`, `"expected string, got integer"`, `"exceeds maxLength of 1024"`, `"required property missing"`, `"not in enum [a, b, c]"`. |

### What MUST NOT appear in the envelope

- The rejected value itself. If the payload had `{"q": "A" * 10000}`, the error reason says `"exceeds maxLength of 1024"`, not `"exceeds maxLength of 1024: AAAAAA..."`.
- Stack traces from `jsonschema.ValidationError.__str__()`. Those often include the full instance. The translation layer in `validation.py` must explicitly strip them.
- Timing information, memory metrics, or internal state.

### Translation from `jsonschema.ValidationError`

The translation layer in `llm-tooling/mcp/validation.py` maps the jsonschema error model onto this envelope:

| jsonschema field | → envelope field | Translation |
|---|---|---|
| `validator` (e.g., `"type"`, `"required"`, `"additionalProperties"`) | → `error.reason` (via lookup table) | Static message per validator, never includes `instance` |
| `path` (deque) | → `error.field` | Joined with `/` prefix to form a JSON Pointer |
| `validator_value` | → `error.reason` (where applicable) | Used to compose messages like "exceeds maxLength of 1024" |
| `instance` | DISCARDED | Never included in the envelope |
| `schema_path` | DISCARDED | Internal detail; not useful to callers |

### CLI subprocess guarantee

On validation failure, `execute_tool` MUST return the error envelope **without invoking `subprocess.run`**. The failing code path exits the function before `adapter.run_command(argv)` is called. This is verified by unit tests that mock `subprocess.run` and assert it was never called for rejected payloads.

---

## Cross-cutting: determinism and ordering

All four data shapes above are deterministic. For the specific sort keys of the `redaction_postcondition.misses` array, see `contracts/postcondition-manifest.md` §"Ordering determinism" which is the source of truth — this section summarizes but does not redefine.

- **Manifest fields** sort arrays (`misses`, `source_records`) by stable keys. For `misses`, the sort order is `(path, field, category)` as specified in `contracts/postcondition-manifest.md`. For `source_records`, the key is `source_hash`. Identical inputs produce identical JSON output.
- **Detector categories** appear in summary reports in a stable order (alphabetical by category name).
- **Stderr warnings** emit in a stable order (symlink refusal summary after all walk output, Neo4j warning before any connection attempt). Multiple warnings within one run are ordered by when they were discovered.
- **Validation errors** translate jsonschema path tuples to JSON Pointer strings via a deterministic join; errors from the same violation produce the same pointer regardless of jsonschema version (within the `>=4,<5` pin).

---

## Not introduced by this spec

The following data-model changes are **out of scope** for Spec 027 and are documented here only to prevent them from being accidentally bundled:

- No new entity type, no new link type, no new shard directory.
- No schema version bump. `ARTIFACT_SCHEMA_VERSION` stays at its current value (`v1`).
- No changes to existing manifest fields (`sources[]`, `artifacts[]`, `outputs_hash`, etc.).
- No new config fields in `pkg.yaml`. All behavior is CLI-flag or env-var driven.
- No changes to the redaction key storage (`secrets/redaction.key`).
- No changes to the existing run-manifest file names (still `<stage>-manifest.json`).
