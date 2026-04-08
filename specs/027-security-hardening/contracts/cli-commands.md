# Contract: CLI command surface

Defines the exact flag list, help text behavior, exit codes, and stderr side effects for every CLI command that Spec 027 modifies or adds. Backwards compatibility is a hard constraint — every new flag is additive and optional, and every existing invocation must continue to behave identically in its default mode.

## Exit code allocation

Spec 027 introduces two new distinct exit codes. The full CLI exit-code vocabulary after Spec 027 is:

| Code | Meaning | Owner |
|---|---|---|
| 0 | Success (includes `status: "tolerated"` for postcondition) | all commands |
| 1 | Generic error / unhandled exception | Python / argparse catch-all |
| 2 | argparse error (unknown flag, missing required arg, etc.) | argparse default |
| **3** | **Redaction postcondition detected a miss and the user did not pass `--allow-redaction-misses`** (NEW) | `auditgraph rebuild` |
| **4** | **Neo4j plaintext URI refused because `--require-tls` or `AUDITGRAPH_REQUIRE_TLS=1` is set** (NEW) | `auditgraph sync-neo4j`, `auditgraph export-neo4j` |
| Other non-zero | Command-specific errors (path containment, budget exceeded, etc.) | various |

Exit codes 3 and 4 MUST be distinct from all other exits the same command might produce so that CI callers can dispatch on them.

---

## `auditgraph ingest` (MODIFIED)

### New flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--allow-symlinks` | boolean switch | absent | **RESERVED.** Recognized by argparse but raises `NotImplementedError` at dispatch time with a message pointing at the issue tracker for use-case discussion. MUST NOT be silently accepted as a no-op. See FR-004a. |

### Behavior changes

- Per-path symlink containment check added to the walker (FR-001 through FR-004).
- Symlinks whose resolved target falls outside the workspace root (or whose target does not exist) are skipped with `skip_reason: "symlink_refused"` in the ingest manifest.
- When ≥ 1 symlink is refused, a single summary line is emitted to stderr at the end of the run: `WARN: refused N symlinks pointing outside <absolute_workspace_root> (see manifest for details)`.
- Intra-workspace symlinks (resolved target stays inside the workspace root) are processed normally.

### Exit codes

- `0`: successful ingest, regardless of whether any symlinks were refused
- `2`: argparse error (e.g., `--allow-symlinks` without a value if argparse were to require one — it doesn't; this is for unknown flags)
- `1`: any other unhandled error

### Backwards compatibility

- A workspace with no symlinks at all behaves identically to pre-Spec-027 behavior.
- A workspace with only intra-workspace symlinks behaves identically.
- A workspace with escaping symlinks previously ingested their targets into the chunk store; post-Spec-027 it does not, and emits the stderr warning. **This is a behavior change on hostile workspaces** and is the intended fix for H1.

---

## `auditgraph import <paths...>` (MODIFIED)

Same flag additions and same behavior changes as `ingest`. The `--allow-symlinks` flag and the symlink containment check apply identically. The stderr summary line uses the same format.

### Exit codes

Same as `ingest`.

---

## `auditgraph rebuild` (MODIFIED)

### New flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--allow-redaction-misses` | boolean switch | absent | When present, the pipeline redaction postcondition (FR-025) reports misses in the run manifest as `status: "tolerated"` instead of failing the run. Exit code becomes 0 (tolerated) rather than 3 (fail). The manifest records `allow_misses: true` so the bypass is auditable. |

### Behavior changes

- A new redaction postcondition runs as the final step of `run_rebuild` (FR-025, FR-028).
- On a clean run, the postcondition emits `redaction_postcondition: {"status": "pass", "misses": [], "allow_misses": false, ...}` in the rebuild's final manifest.
- On a dirty run without `--allow-redaction-misses`, the postcondition emits `status: "fail"`, exits the process with code 3, and surfaces the misses via the manifest.
- On a dirty run WITH `--allow-redaction-misses`, the postcondition emits `status: "tolerated"`, records the misses, and exits 0.

### Exit codes

- `0`: pipeline succeeded and postcondition passed, OR postcondition detected misses but `--allow-redaction-misses` was passed
- `1`: generic pipeline error at any earlier stage
- `2`: argparse error
- **`3`**: postcondition detected misses and the user did not pass `--allow-redaction-misses` (NEW)

### Backwards compatibility

- A clean workspace with no redaction issues behaves identically to pre-Spec-027 (the postcondition passes silently and the exit code stays 0).
- A workspace that was poisoned pre-Phase-1 hotfix and has NOT been rebuilt post-hotfix will likely fail the postcondition — this is the intended alert that the user needs to re-ingest from clean sources or run `validate-store` first.

---

## `auditgraph export-neo4j` (MODIFIED)

### New flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--require-tls` | boolean switch | absent | When present (or when `AUDITGRAPH_REQUIRE_TLS=1` is set in the environment), non-localhost Neo4j connections with `bolt://` or `neo4j://` schemes are refused with exit code 4 instead of emitting a warning. |

### Behavior changes

- **Path containment fix (FR-010)**: the `--output` flag is now validated against `ensure_within_base(<resolved_output>, <root>/exports/neo4j)` before the Cypher file is written. Previously accepted arbitrary absolute paths.
- **Default output path (FR-011)**: when `--output` is omitted, writes to `<root>/exports/neo4j/export.cypher` (newly defined deterministic default).
- Non-localhost `bolt://`/`neo4j://` URIs emit the plaintext warning (see `sync-neo4j` entry below for the warning line format — shared behavior).
- With `--require-tls`, non-localhost plaintext refused with exit code 4 and no connection attempted.

### Exit codes

- `0`: successful export
- `1`: generic error (file write failure, etc.)
- `2`: argparse error
- **`4`**: Neo4j plaintext URI refused because `--require-tls` is set (NEW)
- Other non-zero: budget exceeded, path containment violation, etc.

### Backwards compatibility

- Users with existing invocations that passed `--output exports/neo4j/mine.cypher` (workspace-relative) continue to work identically.
- Users with existing invocations that passed an absolute external path (`--output /tmp/foo.cypher`) will start receiving a path-containment error. **This is an intentional breaking change** for H3 and is documented in the CHANGELOG.
- Users with `bolt://remote-host` who do NOT set `--require-tls` will see a new stderr warning but their export still succeeds.

---

## `auditgraph sync-neo4j` (MODIFIED)

### New flags

Same `--require-tls` flag as `export-neo4j`, with identical semantics. Also honors `AUDITGRAPH_REQUIRE_TLS=1`.

### Behavior changes

- Non-localhost `bolt://`/`neo4j://` URIs emit a single stderr warning line at connection setup:
  ```
  WARN: Neo4j URI uses unencrypted scheme against non-localhost host <host>. Consider using bolt+s://<host>:<port> to protect credentials in transit.
  ```
- With `--require-tls` or `AUDITGRAPH_REQUIRE_TLS=1`, the warning is replaced with a refusal: stderr gets `ERROR: --require-tls set: refusing Neo4j connection to <host> over unencrypted scheme <scheme>` and the process exits with code 4. No connection is attempted.
- Loopback hosts (`localhost`, `127.0.0.1`, `::1`) are exempt from both warning and refusal regardless of scheme.

### Exit codes

- `0`: successful sync (or dry-run success)
- `1`: generic Neo4j error, connection failure, etc.
- `2`: argparse error
- **`4`**: Neo4j plaintext URI refused because `--require-tls` is set (NEW)

### Backwards compatibility

- Users with `bolt://localhost` or `bolt+s://remote` see no change.
- Users with `bolt://remote` see a new stderr warning but sync proceeds.
- Users with `bolt://remote` + `--require-tls` see refusal (they had to opt in, so this is the intended behavior).

---

## `auditgraph validate-store` (NEW command)

### Synopsis

```
auditgraph validate-store [--root ROOT] [--config CONFIG] [--profile NAME | --all-profiles] [--format json|text]
```

### Purpose

Audit an existing `.pkg/profiles/<profile>/` store for strings matching the current redaction detector allowlist. Strictly read-only. Used by operators whose stores may have been poisoned before the Phase 1 C1 hotfix landed and who want a fast "am I poisoned?" check without running a full `auditgraph rebuild`.

### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--root` | path | `.` | Workspace root containing the `.pkg/` directory. Matches the convention used by other auditgraph commands. |
| `--config` | path | (auto-detected) | Config file path. Used to determine which profile is "active" in the absence of `--profile`. |
| `--profile <name>` | string | (active profile from config) | Override the active profile. Mutually exclusive with `--all-profiles`. |
| `--all-profiles` | boolean switch | absent | Scan every profile under `.pkg/profiles/*/`. Mutually exclusive with `--profile`. |
| `--format` | enum `json \| text` | `text` | Output format. `text` is human-readable; `json` is machine-readable (same shape as the postcondition manifest entry, for consistency). |

### Scope (FR-019)

The command scans the following directories under each selected profile:
- `entities/<shard>/*.json`
- `chunks/<shard>/*.json`
- `segments/<shard>/*.json`
- `documents/*.json`
- `sources/*.json`

The command does NOT scan:
- `runs/` — pipeline manifests, contain SHA-derived run IDs that false-positive on entropy detectors
- `indexes/` — derived data; if entities are clean, indexes are clean by construction
- `secrets/` — the redactor's own HMAC key

### Exit codes

- `0`: no misses detected, OR no `.pkg/profiles/` directory exists ("no store to validate" message)
- `1`: one or more misses detected (regardless of profile count)
- `2`: argparse error
- Other non-zero: unreadable store, permission denied, etc.

### Output format (text)

Clean store:
```
No redaction misses detected.
Scanned: 12847 shards across 1 profile(s) in 312ms.
```

Poisoned store (text mode):
```
REDACTION MISSES DETECTED
Profile: default
  chunks/ab/cd1234.json (credential in field `text`)
  chunks/ef/gh5678.json (cloud_keys in field `text`)
  sources/9a8b7c.json (vendor_token in field `path`)

Scanned: 12847 shards across 1 profile(s) in 312ms.
Exit code: 1
```

### Output format (json)

Matches the `redaction_postcondition` manifest shape from `data-model.md §1`, plus a top-level `profiles` wrapper when `--all-profiles` is in effect:

```json
{
  "profile": "default",
  "status": "fail",
  "misses": [
    {"path": "chunks/ab/cd1234.json", "category": "credential", "field": "text"}
  ],
  "scanned_shards": 12847,
  "wallclock_ms": 312
}
```

With `--all-profiles`:

```json
{
  "profiles": {
    "default": { ... as above ... },
    "dev": { ... },
    "scratch": { ... }
  },
  "total_misses": 4,
  "poisoned_profiles": ["default", "dev"]
}
```

### Backwards compatibility

This is a new command. No existing invocation is affected.

---

## Summary of CLI changes

| Command | New flags | Changed default behavior | New exit codes |
|---|---|---|---|
| `ingest` | `--allow-symlinks` (reserved, NotImplementedError) | Symlinks escaping workspace now refused | — |
| `import` | `--allow-symlinks` (reserved, NotImplementedError) | Symlinks escaping workspace now refused | — |
| `rebuild` | `--allow-redaction-misses` | New postcondition at end of run | `3` (postcondition fail) |
| `export-neo4j` | `--require-tls` | `--output` path containment; deterministic default path; stderr warning on plaintext remote | `4` (require-tls refusal) |
| `sync-neo4j` | `--require-tls` | Stderr warning on plaintext remote | `4` (require-tls refusal) |
| `validate-store` | ENTIRE COMMAND | — | `1` (misses detected) |

All new flags follow the existing auditgraph convention: lowercase with dashes, no single-character aliases, clearly documented in `--help` output.
