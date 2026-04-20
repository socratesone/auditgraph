# 026 — Security Hardening (Pre-spec Notes)

**Status**: Pre-spec notes — NOT ready for `/speckit.specify`. Capture phase only.
**Created**: 2026-04-07
**Author of these notes**: Joshua Albert (via session with Claude)
**Trigger**: Post-Spec-025 security pass combining Abaddon, Slop Sentinel, and an aegis deep audit.

This file is a stash for a future spec. It is not a spec yet. When this work
is ready to begin, run `/speckit.specify` against the distilled requirements
below and let it bloom into a real spec. Phase 1 (C1 redactor bypass) is
urgent and should probably ship as its own PR *ahead* of the formal spec flow
— see "Priority and sequencing" below.

---

## Executive summary

Auditgraph is structurally clean: no `pickle`/`eval`/`shell=True` anywhere,
YAML loading is universally `safe_load`, Cypher generation is parameterized,
filter parsing is injection-safe, dependencies currently have no known CVEs.

The two automated scanners collectively produced **226 "findings" of which
zero were actionable** — all were regex-pattern entropy hits, test-fixture
secrets, and layout conventions that don't match auditgraph's spec-organized
test layout. The real risks surfaced only from the aegis deep audit, and
every one was verified by direct code reading before being recorded here.

| # | Severity | Finding | Verified at |
|---|---|---|---|
| C1 | **CRITICAL** | Redactor is bypassed for `chunks/`, `segments/`, `documents/` writes — the core trust-boundary feature of the project is broken | `pipeline/runner.py:190` → `storage/artifacts.py:77,83,89` |
| H1 | HIGH | Ingest walker follows symlinks without per-path containment check → hostile workspace can exfiltrate `/etc/passwd`, `~/.ssh/id_rsa`, `~/.aws/config` into the chunk store | `ingest/scanner.py:21`, `ingest/importer.py:21` |
| H2 | HIGH | MCP server passes `payload` dict straight to CLI argv construction with no jsonschema validation; manifest `additionalProperties: false` is documentation-only | `llm-tooling/mcp/server.py:71` → `llm-tooling/mcp/adapters/project.py:46-52` |
| H3 | HIGH | `auditgraph export-neo4j --output <path>` accepts arbitrary absolute paths with no containment check (sister command `export` does) | `cli.py:443-449` vs `cli.py:359-389` |
| M1 | MEDIUM | Redaction detector allowlist misses AWS/GCP/Azure keys, OpenAI/Anthropic/Stripe tokens, and common variant keywords (`aws_access_key_id`, `auth_token`, `passwd`) | `utils/redaction.py:112-131` |
| M2 | MEDIUM | Even once C1 is fixed, PEM private keys crossing a 200-token chunk boundary still escape redaction because detectors require matched `BEGIN`/`END` markers in one chunk | `utils/redaction.py:91-98` + `utils/chunking.py:10-36` |
| L1 | LOW | `bolt://` (plaintext) Neo4j URIs accepted for non-localhost hosts | `neo4j/connection.py:30` |

**Plus one infrastructural finding worth threading into the spec:**

- **`PipelineRunner` god class** (`pipeline/runner.py`, 885 lines, cyclomatic
  complexity 136). Not a security finding *per se*, but **C1 exists precisely
  because the runner is too big to keep redaction invariants straight** — the
  unredacted `write_document_artifacts` path and the redacted
  `write_json_redacted` path live inside `run_ingest` 25 lines apart, and
  the bug is that the wrong one was called first. Decomposition would make
  this class of bug structurally harder to reintroduce.

---

## The C1 bug, stated precisely

The project's README and `tests/test_spec011_ingest_redaction.py` describe
redaction as a guarantee: "Auditgraph ingests notes and scrubs
credential-shaped strings before they hit persistent storage." The
implementation delivers this guarantee for exactly one artifact shape —
`pkg_root/sources/<hash>.json` — because that's the only write routed through
`write_json_redacted`. The `chunks/`, `segments/`, and `documents/` writes in
`run_ingest` lines 189-190 carry the raw document text (built in
`ingest/parsers.py:91-107` straight from `chunk_text(text, ...)`) and are
committed to disk with unmodified `write_json`.

Any credential the detector set would have caught — a JWT, a bearer token, a
`password=...` line, a PEM private key, a `ghp_` token — persists in
cleartext under `.pkg/profiles/<profile>/chunks/<shard>/<chunk_id>.json`.

The Spec 011 test suite confirms the bug-by-omission: it walks only
`pkg_root / "sources"` when grepping for sentinels. It has never asserted
the shard stores are clean. The Neo4j export code in
`neo4j/records.py:69,100,124` re-runs the redactor at read time, which is
why this hasn't produced a visible leak on the export path — but on-disk
artifacts are still poisoned.

### Blast radius

Anyone with read access to `.pkg/` recovers the cleartext. That includes:
- Backup tooling
- Cloud sync clients (Dropbox, iCloud, OneDrive)
- `git add .pkg` accidents
- Shared dev-container mounts
- Any future feature that emits the chunk text unchanged (preview, search
  highlighting, LLM retrieval, semantic/vector index once that's wired in)

A user who takes the README's redaction promise at face value and pipes
their real notes into auditgraph has, in practice, copied all their
credentials into a second, structurally-indexed store.

---

## Proposed fix architecture for C1 (and M2 as a side effect)

The clean fix is to **move redaction to the boundary where text enters the
chunk pipeline**, not after chunks exist. That solves C1 and M2 together
because redaction-before-chunking means multi-line secrets can't be split
across chunk boundaries.

1. In `ingest/parsers.py:_build_document_metadata`, redact `text` once at the
   top of the function, before `chunk_text(...)` is called. This means:
   - The document body, all segments, and all chunks inherit redacted text
     by construction.
   - PEM keys and other multi-line secrets are redacted before chunking, so
     chunk boundaries cannot split them.
   - `write_document_artifacts` can stay unchanged — it's writing
     already-clean data.
2. In `pipeline/runner.py:run_ingest`, thread the `redactor` into
   `parse_file(...)` via `parse_options` so the parser has access to it
   without importing from the runner.
3. The existing `write_json_redacted` call for `sources/<hash>.json` stays —
   the source record metadata (original path, timestamps, parse_id) is a
   separate concern.
4. **Defense-in-depth postcondition**: run `redactor.detect(...)` across
   every newly written shard under `chunks/`, `segments/`, `documents/` and
   fail the run on any hit. This catches future regressions — if someone
   adds a new shard type without running it through the redactor, the
   postcondition fires.

---

## Test plan (per-finding)

### C1 + M2 — `tests/test_spec011_ingest_redaction.py`

Three new assertions:

1. **Shard coverage**: after ingesting a document containing each sentinel
   (JWT, PEM, bearer token, AWS key, `password=` line), walk
   `pkg_root/chunks/**/*.json`, `pkg_root/segments/**/*.json`,
   `pkg_root/documents/*.json` and assert the sentinel is absent from the
   `text` field of every chunk, the `text` field of every segment, and any
   string field of every document.
2. **Cross-chunk PEM**: generate a synthetic document with a real-shape
   2048-bit RSA PEM key padded with 800 tokens of filler on each side,
   ingest with default chunk size 200, and assert no chunk contains a
   contiguous base64 run longer than 40 characters.
3. **Postcondition**: ingest a fixture, manually mutate one chunk on disk
   to re-inject a credential, run `auditgraph rebuild`, and assert the
   pipeline fails with `redaction.postcondition_failed`.

### H1 — new test `tests/test_spec026_ingest_symlink_containment.py`

Creates a workspace with `notes/leak.md -> /etc/passwd` (or a tmp-file
target under /tmp for portability), runs ingest, and asserts either:
- (a) the symlink is skipped with reason `symlink_refused`, or
- (b) an error is raised
— whichever direction the spec takes (see open question Q1).

### H2 — new test `llm-tooling/tests/test_mcp_payload_validation.py`

Submits `{"unknown_key": "x"}` to every tool in `tool.manifest.json` and
asserts `execute_tool` raises before invoking `subprocess.run`. Also
submit a 1 MiB string value and assert size-cap rejection.

### H3 — extend `tests/test_export_neo4j.py`

Pass `output="/tmp/attacker"` (absolute, outside workspace) and assert
`ensure_within_base` rejects it. Mirror the existing coverage on the
`export` command.

### M1 — `tests/test_redaction_detectors.py`

One positive test per added format: AKIA, AIza, sk-/sk-ant-/sk_live_,
github_pat_, gh[opsur]_, xoxe.xoxp-, aws_access_key_id=,
auth_token=, passwd=, bearer=, auth=.

### L1 — `tests/test_neo4j_connection.py`

Set `NEO4J_URI=bolt://example.com:7687` and assert a warning is logged
(or the connection is refused, per open question Q6).

---

## Priority and sequencing

### Phase 1 — Critical fix (one PR, must ship before any other work)

**Treat as a security hotfix, not spec work.** The formal spec flow is
appropriate for Phases 2-4 but would slow down C1 unacceptably given the
severity.

- Fix C1 by moving redaction into `_build_document_metadata`
- Add shard-coverage assertions to `tests/test_spec011_ingest_redaction.py`
- Add pipeline postcondition
- CHANGELOG entry under `## Unreleased` flagging this as a security fix
- README note recommending users rebuild any existing `.pkg/` that may
  have ingested sensitive material
- Do NOT bundle Phase 2 into this PR — small PR, fast review

### Phase 2 — High findings (single spec, batch PR)

- H1 symlink containment in `scanner.py` and `importer.py`
- H2 MCP jsonschema validation + size caps
- H3 export-neo4j path containment (mirror the `export` handler)
- One regression test per fix

### Phase 3 — Medium fixes

- M1: expand credential detector allowlist; one positive test per added format
- M2: falls out of the Phase 1 fix automatically (redaction pre-chunking), but
  add the cross-chunk PEM test to prove it

### Phase 4 — Defense in depth (optional, separable)

- L1: warn on non-localhost `bolt://`
- New `auditgraph validate-store` CLI command that audits an existing
  `.pkg/` and reports any detected credentials in shards (gives users a
  remediation path for already-poisoned stores from before the Phase 1 fix)
- Pin lower bounds for `pyyaml`, `pypdf`, `python-docx` in
  `pyproject.toml:21-28` so dependency audits are reproducible
- Address the `PipelineRunner` god-class (885 lines, cyclomatic complexity
  136) — not a security fix, but prevents future C1-shaped bugs

---

## Verified-clean areas (do not re-audit unless code changes)

These were checked during the aegis pass and are clean as of commit
`08a4382` (main, post-merge of PR #38):

- No `pickle`, `marshal`, `eval()`, `exec()`, `os.system`, `shell=True`
  anywhere in `auditgraph/` or `llm-tooling/`. The single `subprocess.run`
  call in `mcp/adapters/project.py:58` passes a list, no shell.
- All `yaml.*` call sites use `safe_load`: `config.py:132`,
  `jobs/config.py:16`, `utils/quality_gates.py:31`,
  `utils/mcp_manifest.py:33`.
- Cypher generation: `neo4j/records.py:37-43` sanitizes labels;
  `cypher_builder.py` emits JSON-encoded literals; `sync.py:53-87` uses
  parameterized `$id`/`$props`. No string concatenation sinks.
- Filter parser (`query/filters.py:26-103`): pure string/numeric
  comparisons, no regex compilation of user input.
- BM25 query (`query/keyword.py:33-93`): dict lookup + Python `in`, no
  regex. ReDoS-safe.
- Path containment via `ensure_within_base` is correct at:
  `storage/artifacts.py:40`, `ingest/scanner.py:15` (at the include-root
  level only — see H1), `ingest/importer.py:15` (same caveat),
  `jobs/reports.py:16`, `cli.py:370` (export only — see H3).
- Git provenance reader (`auditgraph/git/reader.py`): dulwich object
  reads, no shell, safe byte decoding.
- Dependency CVE baseline: `pip-audit` clean against current
  `requirements.txt` / `pyproject.toml`.

---

## Open questions for `/speckit.clarify`

1. **H1 symlink policy**: skip symlinks silently, surface as a new
   `skip_reason: symlink_refused`, or hard-error the ingest?
   (Recommendation: surface as skip reason, add a test, document in README.)
2. **C1 migration**: users with existing poisoned `.pkg/` stores — does the
   fix ship with an automatic rebuild trigger, a CHANGELOG warning only, or
   a new `validate-store` command (Phase 4) that reports the risk?
3. **Postcondition strictness**: should the redaction postcondition fail the
   run (blocking), or warn and continue?
   (Recommendation: fail the run by default, `--allow-redaction-misses` flag
   for emergency bypass.)
4. **Detector format for cloud keys (M1)**: define a new `cloud_keys`
   detector category, or extend `vendor_token` to cover it?
   (Recommendation: new `cloud_keys` detector so the category label remains
   meaningful in reports and the `vendor_token` detector stays
   narrowly-scoped to github/slack formats.)
5. **MCP schema validation (H2)**: use `jsonschema` (new dependency) or
   hand-rolled?
   (Recommendation: jsonschema; it's a mature, small, widely-used package
   and the manifest already uses jsonschema-flavored syntax via
   `input_schema`.)
6. **L1 enforcement**: refuse `bolt://` to non-localhost, or warn only?
   (Recommendation: warn only by default, `--require-tls` flag to refuse.)

---

## Constitution & scope

This hardening work is compatible with the non-negotiables in
`.specify/memory/constitution.md`:

- **Determinism** preserved — redaction is deterministic.
- **Local-first** preserved — no new network calls.
- **Backwards compatibility**: the CLI surface gains optional flags only;
  existing invocations keep behaving identically. The on-disk shard format
  does not change; only the *content* (redacted vs not) differs for users
  who had unredacted credentials in their source documents. A user rebuild
  after the Phase 1 fix is equivalent to a normal `auditgraph rebuild`.
- **No co-author trailers** on commits.
- **Tests before code**: every phase has failing-first tests defined above.

---

## Source scanner triage (why Abaddon and Slop Sentinel didn't surface these)

### Abaddon (21 MUST findings — all false positives)

Abaddon's detectors fire on high-entropy substrings, which in auditgraph's
codebase means:

- `neo4j/connection.py:29,31,57,59` — error-message strings mentioning
  `NEO4J_PASSWORD` (the word, not a value)
- `neo4j/cypher_builder.py:34,62,78` — Cypher literal-escape helpers
- `neo4j/records.py:40` — the literal `token = "entity"` (variable name
  pattern match, not actual secret)
- `pipeline/runner.py:254,456,508,650,725,779` — SHA-derived run IDs and
  stage IDs
- `extract/content.py:138`, `extract/ner.py:1`, `extract/ner_backend.py:1` —
  module docstrings
- **`utils/redaction.py:109,116,129` — the regex patterns that DETECT
  credentials**. Abaddon matched its own detector source.

None of these are secrets. Abaddon is useful for catching checked-in
`sk_live_...` strings on other projects; for auditgraph it's noise.
Consider adding per-line suppression markers so future Abaddon runs are
clean.

### Slop Sentinel (205 findings — 4 block_merge, 195 warning, 6 info)

Block-merge findings:

1. **`PipelineRunner` god class** (885 lines, complexity 136) — *real*, see
   Phase 4 above.
2. **Hardcoded high-sensitivity values in `tests/fixtures/git/generate_fixtures.py`** — false positive (fixture generator)
3. **Hardcoded high-sensitivity values in `tests/test_failure_paths.py`** — false positive (intentional test data)
4. **Hardcoded high-sensitivity values in `tests/test_redaction_detectors.py`** — false positive *by definition*: this file's job is to feed credential-shaped strings to the redactor

Warning-tier with real signal:

- Duplication of `_load_reverse_index` across `auditgraph/query/git_introduced.py`, `git_log.py`, `git_who.py` — 3 copies. Real refactor opportunity: extract into `auditgraph/query/_git_common.py`. Not part of this spec.
- Duplication of `_load_manifest` between `llm-tooling/tests/test_adapters.py` and `llm-tooling/tests/test_manifest_contract.py` — minor, not part of this spec.

Noise:

- 116 `test_weakness` findings of the form "no `test_<name>.py` for module `<name>.py`". auditgraph's test layout is spec-organized (`test_spec<NNN>_*.py`), not mirror-organized, so this metric doesn't fit the project. Tunable, not actionable.

### What the scanners missed

Neither automated tool caught C1, H1, H2, H3, M1, or M2. C1 in particular
is invisible to grep-based tooling because it's an *absence* of a call, not
a presence of a bad pattern. The Spec 011 test suite missed it because the
assertion walks only the `sources/` directory, not the chunk store — a bug
of omission in the test, not the production code. The aegis model-driven
pass caught it by reading the redactor, tracing every call site, and
noticing the asymmetry.

**Lesson for future audits**: for trust-boundary features, grep for the
inverse — every place that writes to a sensitive artifact path, not every
place that *might* contain a secret. `rg -n "write_json\(.*pkg_root.*chunks"` finds the bug in one line.

---

## When to revisit

Run `/speckit.specify` against this after Phase 1 ships as a hotfix. Phases
2-4 should share a single spec `026-security-hardening`. Do not let Phase 1
wait on the spec process.
