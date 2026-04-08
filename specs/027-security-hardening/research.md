# Phase 0 Research — Spec 027 Security Hardening

**Date**: 2026-04-07
**Purpose**: Resolve the five research items surfaced in `plan.md` Phase 0. Every item is a narrow lookup against the current venv, the current codebase, or library documentation — no broad research tasks and no external agents were needed.

---

## R1. Dependency lower-bound versions for the parser pin (FR-029)

**Decision**: Pin the three untrusted-input parsers in `pyproject.toml` at:

```toml
"pyyaml>=6.0.3",
"pypdf>=6.9.1",
"python-docx>=1.2.0",
```

No upper bounds. Let pip resolve forward unless a specific incompatibility is discovered during testing.

**Rationale**: These are the versions currently installed in the venv that passed the 805-test suite after the Phase 1 hotfix merged (verified 2026-04-07 via `pip show`). Pinning *at or above* the post-hotfix baseline guarantees fresh installs land on a version that has been end-to-end-tested against the current code and is free of any CVEs known to `pip-audit` as of the audit session. Users who want a specific newer version can override; users who want any-version-whatever still get a secure floor.

**Alternatives considered**:

- **Pin to the exact current version** (`pyyaml==6.0.3`): rejected. Exact pins conflict with downstream consumers and force churn on every security release. Lower-bound pinning is the standard pattern for libraries.
- **Pin to the major version only** (`pyyaml>=6`): rejected. `pyyaml 6.0.0` and `6.0.3` differ in several CVE-adjacent fixes; pinning to `>=6` leaves users exposed to any old 6.0.x release.
- **Pin with an upper bound** (`pyyaml>=6.0.3,<7`): considered but rejected as default. Upper bounds create an artificial release gate every time the library majors. The spec explicitly allows adding an upper bound *if a specific incompatibility is discovered during testing* (FR-029 language), but the default is lower-only.
- **Skip pinning entirely and rely on `pip-audit` CI gate**: deferred. Clarification Q8 decided the CI gate belongs in a follow-up maintenance spec. FR-029 closes the immediate window.

---

## R2. Neo4j URI scheme allowlist for the FR-023 warning

**Decision**: The "unencrypted" set is exactly `{"bolt://", "neo4j://"}`. The "encrypted" set is exactly `{"bolt+s://", "neo4j+s://"}`. No other schemes are valid in the current allowlist and none need to be added.

**Rationale**: The existing allowlist in `auditgraph/neo4j/connection.py:30` is:

```python
if not uri.startswith(("bolt://", "neo4j://", "bolt+s://", "neo4j+s://")):
```

This matches Neo4j's current driver scheme set (Neo4j 5.x docs, same schemes on Neo4j 4.x). The deprecated `bolt+routing://` scheme from Neo4j 3.x is not in the current allowlist, is not supported by the Neo4j 5.x driver, and does not need special handling — if a user supplies it, they hit the existing `ValueError` well before the TLS check runs. The `ssc` (self-signed certificate) variants `bolt+ssc://` and `neo4j+ssc://` exist in some older drivers but are not in the current auditgraph allowlist and are out of scope for this spec.

**Alternatives considered**:

- **Add `bolt+ssc://` / `neo4j+ssc://` as encrypted variants**: rejected. Self-signed is encrypted but provides no identity verification; treating it as "secure" would be misleading. Not adding them to the allowlist preserves today's behavior.
- **Warn on every non-`+s://` scheme, even unknown ones**: rejected. The allowlist rejects unknown schemes entirely, so a warning code path for them is unreachable.
- **Distinguish between "unencrypted loopback OK" and "unencrypted remote NOT OK" at the allowlist level**: considered, but the cleaner separation is to keep the allowlist scheme-only and apply the loopback check in the warning/refusal code path (per FR-024). Keeps the allowlist single-purpose.

---

## R3. Safe base64 run length for the cross-chunk PEM regression test (SC-005)

**Decision**: 40 characters of continuous `[A-Za-z0-9+/=]` is the threshold. Any chunk containing a run longer than 40 characters of that character class, after ingest of a synthetic PEM-bearing document, fails the SC-005 assertion.

**Rationale**: We need a threshold that:

1. **Is below the shortest legitimate PEM body segment**: a 2048-bit RSA PEM private key's base64 body is typically 50-64 characters per line, with the entire body running to ~1600 characters. A 40-character threshold catches any single line of the body.
2. **Is above the longest legitimate non-secret base64-shaped string**: the candidates to worry about are SHA-256 hex hashes (64 characters, but hex only, so it doesn't contain `+` or `/`), UUIDs (36 characters with hyphens, or 32 without, short of the threshold), JWT segments (variable but typically >40 chars — but JWTs are already caught by the dedicated `jwt` detector and would be redacted before they reach this assertion), and markdown citation tokens like `[^abc123]` which never exceed a dozen characters.
3. **Is low enough that a buggy redactor can't hide behind it**: if the threshold were 100 characters, a partial leak of only the first 60 characters of a key body would go undetected. 40 characters is narrow enough that any contiguous partial leak of the body gets caught.

The one edge case: SHA-256 BASE64-encoded (not hex) is exactly 44 characters and contains `[A-Za-z0-9+/=]`. We need to either (a) accept that SHA-256 base64 in chunk text will trigger the assertion and design test fixtures not to contain it, or (b) raise the threshold to 48 characters (below the RSA-2048 line length but above SHA-256 base64). **Decision: use 40 characters and ban SHA-256 base64 from fixture documents.** The test is a regression check, not a production runtime filter; we control the fixture content.

**Alternatives considered**:

- **50 characters**: rejected. Too permissive; a partial key body leak could slip under.
- **20 characters**: rejected. Too aggressive; will match short base64 runs that appear naturally in markdown code fences or URL-encoded blobs.
- **Match the exact PEM regex rather than a character-class heuristic**: rejected for this specific assertion. The test is a *regression guard* for the "cross-chunk escape" failure mode — it's asserting that the base64 body does not survive anywhere in the chunk store. The PEM regex itself is already used in production by the redactor; the test's job is to catch the case where the regex fails to match (because the markers are absent from the chunk), which means the heuristic has to work *without* the markers.

---

## R4. jsonschema Draft 7 feature coverage for the manifest's existing syntax (FR-005)

**Decision**: Use `jsonschema>=4,<5` with the default Draft 7 validator. All features currently used in `llm-tooling/tool.manifest.json` are supported.

**Rationale**: Reviewed the features used in the current manifest against the jsonschema library's supported keyword list for Draft 7:

| Feature | Used in manifest? | Draft 7 support? |
|---|---|---|
| `"type": "object"` | Yes | Yes |
| `"type": "string"` | Yes | Yes |
| `"type": "integer"` | Yes | Yes |
| `"type": "boolean"` | Yes | Yes |
| `"properties": {...}` | Yes | Yes |
| `"required": [...]` | Yes | Yes |
| `"additionalProperties": false` | Yes | Yes |
| `"enum": [...]` | Yes | Yes |
| `"maxLength": N` | Partial (to be expanded by FR-007) | Yes |
| `"minimum"`, `"maximum"` | Yes (on integer params) | Yes |

None of the features in the manifest require Draft 2019-09 or later (e.g., `unevaluatedProperties`, `$defs`, `$anchor`). Draft 7 is the standard default for `jsonschema >= 4` via `jsonschema.Draft7Validator` or the auto-detected default.

The library currently isn't installed in the venv (verified 2026-04-07 via `python -c "import jsonschema"` → `ModuleNotFoundError`). Implementation will add it to `pyproject.toml` as part of FR-030 and re-install the dev environment.

**Alternatives considered**:

- **`fastjsonschema`**: rejected at clarify time (Q4). Less mature, smaller community, performance gain not relevant.
- **Hand-rolled validator**: rejected at clarify time (Q4). More code, worse error messages, re-implements a fraction of the spec.
- **Draft 2020-12 validator**: not needed. The manifest doesn't use any post-Draft-7 features.

---

## R5. `ensure_within_base` correctly handles resolved symlink targets

**Decision**: The existing `auditgraph/utils/paths.py:ensure_within_base` helper is correct as-is for the H1 symlink containment requirement. No changes to the helper are needed; the fix is purely at the *call site* — calling it on every walked path instead of only on the include root.

**Rationale**: Reading the existing implementation (`auditgraph/utils/paths.py:1-15`):

```python
def ensure_within_base(path: Path, base: Path, *, label: str = "path") -> Path:
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise PathPolicyError(f"{label} must remain within {resolved_base}") from exc
    return resolved_path
```

`Path.resolve()` follows symlinks fully (including symlink chains) and returns the canonical absolute path. If a symlink at `<workspace>/notes/leak.md` points to `/etc/passwd`, `(workspace / "notes" / "leak.md").resolve()` returns `/etc/passwd`. The `relative_to(resolved_base)` call then fails because `/etc/passwd` is not a descendant of the resolved workspace root, and `PathPolicyError` is raised.

This means the Phase 2 symlink-containment fix is purely a *call-site* change: the existing scanner and importer call `ensure_within_base` once on the include root at the start of the walk (`scanner.py:15`, `importer.py:15`), but they do NOT call it on each file yielded by `rglob`. The fix is to add a per-path call inside the walk loop and catch the `PathPolicyError` to convert it into a `symlink_refused` skip (rather than aborting the walk).

The broken-symlink edge case (`FR-004`: "Broken symlinks MUST be skipped with the same `symlink_refused` reason rather than crashing the run"): `Path.resolve(strict=False)` — which is the default — does NOT require the target to exist, so a broken symlink resolves to its textual target path and the containment check proceeds. If the target textually escapes, it's refused. If the target textually stays inside the workspace but doesn't exist, the file is filtered out by `is_file()` later in the walk. Either way, no crash. This behavior is confirmed by `Path.resolve()` documentation and reproducible with a one-line test.

**Alternatives considered**:

- **Add a new `contained_symlink_target` helper with different semantics**: rejected. The existing helper already does the right thing; adding a second one violates DRY.
- **Refuse all symlinks unconditionally at scanner level**: rejected. FR-003 requires intra-workspace symlinks to be processed normally.
- **Use `Path.is_symlink()` to detect symlinks first and only call `resolve` on them**: rejected as optimization that adds complexity. Calling `resolve()` on every walked path is cheap (it's a single system call per path, and the walker already stats every path via `is_file()`).

---

## Summary

All five research items are resolved. No unresolved `NEEDS CLARIFICATION` markers remain. The plan's Phase 1 (data-model.md, contracts/, quickstart.md) can proceed immediately.

| Item | Resolution |
|---|---|
| R1 — Parser pin versions | `pyyaml>=6.0.3`, `pypdf>=6.9.1`, `python-docx>=1.2.0`, lower-bound only |
| R2 — Neo4j scheme allowlist | `{bolt://, neo4j://}` unencrypted; `{bolt+s://, neo4j+s://}` encrypted; no `+ssc` variants added |
| R3 — Base64 threshold for SC-005 | 40 characters of `[A-Za-z0-9+/=]`; fixture must avoid SHA-256 base64 |
| R4 — jsonschema Draft 7 coverage | All manifest features supported; use `jsonschema>=4,<5`, default validator |
| R5 — ensure_within_base correctness | Helper is correct as-is; fix is call-site only in scanner and importer |
