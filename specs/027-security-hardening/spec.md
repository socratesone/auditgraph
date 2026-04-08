# Feature Specification: Security Hardening (Phases 2-4)

**Feature Branch**: `027-security-hardening`
**Created**: 2026-04-07
**Status**: Draft
**Input**: User description: "Security hardening spec, Phases 2-4. Base requirements are in specs/026-security-hardening/NOTES.md. Phase 1 (C1 redactor bypass) already shipped as hotfix 215398d. Confirm during clarify that M2 cross-chunk PEM escape is still open despite the C1 fix — the hotfix redacts chunks post-chunking, not pre-chunking."

## Background and Scope

The post-Spec-025 security audit ran three scanners against the repository: Abaddon, Slop Sentinel, and an aegis deep audit. The aegis pass surfaced seven verified findings (one critical, three high, two medium, one low). The full writeup, per-finding file:line citations, and scanner triage live in `specs/026-security-hardening/NOTES.md`.

**Phase 1 has already shipped.** The critical finding — the redactor was being bypassed for `chunks/`, `segments/`, and `documents/` shards, plus `auditgraph import` bypassed redaction entirely for `sources/` as well — was patched on `main` as commit `215398d` on 2026-04-07 with two new regression tests (`test_ingest_redacts_body_credentials_across_all_shards`, `test_import_redacts_body_credentials_across_all_shards`). The hotfix is closed; this spec does not reopen it.

**This spec covers Phases 2-4 only**: the six remaining findings (H1, H2, H3, M1, M2, L1) plus three defense-in-depth items (a new `validate-store` command so users with pre-hotfix `.pkg/` stores can audit for residual secrets, a dependency-pinning baseline so future audits are reproducible, and a pipeline-level redaction postcondition that fails the run on any missed secret). The `PipelineRunner` god-class decomposition that Slop Sentinel flagged is explicitly **not** in this spec — it is an engineering concern, not a security finding, and its test-surface risk warrants a separate effort.

**Important note on M2 carried forward from the Phase 1 hotfix.** The NOTES document originally recommended fixing C1 by redacting raw document text *before* chunking (so multi-line secrets could not be split across chunk boundaries). The hotfix redacts the already-built chunk payloads *after* chunking because that was the smallest viable change. The consequence is that M2 — a PEM private key whose `-----BEGIN-----` and `-----END-----` markers fall in different chunks — is still open. A 2048-bit RSA key plus surrounding context can exceed the 200-token default chunk size, and the `pem_private_key` detector in `utils/redaction.py` requires both markers in the same input string. User Story 5 and FR-016/FR-017 resolve this in Spec 027.

## Clarifications

### Session 2026-04-07

- Q: M2 fix approach — redact raw document text before chunking, add a cross-chunk detector after chunking, or do both? → A: Redact-before-chunk. Thread the redactor into `parse_options`, redact full document text once inside `_build_document_metadata`, and remove the hotfix's post-chunking redaction pass so there is a single source of truth for redaction in the ingest pipeline.
- Q: Redaction postcondition strictness — fail the run by default or warn and continue? → A: Fail by default with a `--allow-redaction-misses` opt-out flag. Postcondition failure exits with a distinct non-zero status code (proposed: exit 3). The opt-out flag records the tolerated-miss decision in the manifest so the bypass is auditable in shell history and CI logs.
- Q: Symlink policy when an ingested path's real target falls outside the workspace root — skip silently, skip with warning, hard error, or skip + reserve future flag? → A: Skip with `skip_reason: symlink_refused` in the manifest, plus a summary `WARN` line on stderr at end of ingest naming the refused count and the workspace root, plus a reserved `--allow-symlinks` CLI flag that is recognized by argparse but currently raises `NotImplementedError` so the schema is forward-compatible without committing to the behavior in Phase 2.
- Q: MCP payload validation library — `jsonschema`, `fastjsonschema`, hand-rolled, or allowlist-only? → A: `jsonschema` library, pinned `>=4,<5`, with a small translation layer in `llm-tooling/mcp/validation.py` mapping `jsonschema.ValidationError` to the project's structured error shape (tool name, offending field, reason, no echoed value). Pure-Python, ~500 KB total footprint, zero compiled deps, matches the manifest's existing schema syntax.
- Q: `validate-store` command scope — which profiles and which shard directories does it scan? → A: Active profile by default; canonical shards only (`entities/`, `chunks/`, `segments/`, `documents/`, `sources/`); `runs/`, `indexes/`, `secrets/` excluded because they are derived data, pipeline manifests, and the redactor's own key respectively. Accept `--profile <name>` to override the active profile and `--all-profiles` to widen scope. When `--all-profiles` finds at least one poisoned profile, exit code is non-zero and the report breaks down misses per profile. Workspace with no `.pkg/profiles/` → exit zero with "no store to validate".
- Q: Cloud-keys detector category — new `cloud_keys` summary category, extend `vendor_token`, one detector per vendor, or new category with flat regex? → A: New `cloud_keys` summary category covering AWS access key IDs, Google API keys, Anthropic keys, OpenAI keys, and Stripe live keys. `vendor_token` stays narrow to GitHub and Slack developer tokens (expanded to include the new `github_pat_` and `gh[opsur]_` GitHub prefixes). Two categories, two independent failure domains, severity signal preserved in summary reports. Plan phase picks whether `cloud_keys` is one regex with alternation or multiple sub-detectors sharing the category name.
- Q: Neo4j insecure URI enforcement — warn only, warn with opt-in refusal, refuse by default, or config-file strictness? → A: Warn by default on non-localhost `bolt://`/`neo4j://` URIs. Add `--require-tls` CLI flag on `sync-neo4j` and `export-neo4j` plus `AUDITGRAPH_REQUIRE_TLS=1` env var that escalates the warning to a hard refusal with a dedicated non-zero exit code. Backwards-compatible with existing remote `bolt://` deployments while giving compliance users a first-class strict mode.
- Q: Dependency pinning scope — pin the untrusted-input parsers only, pin everything, defer all pinning, or pin + add CI gate? → A: Pin lower bounds for `pyyaml`, `pypdf`, `python-docx` in Spec 027 because those three parse untrusted input and a CVE in any of them is directly exploitable via `auditgraph ingest`. Defer broader pinning (neo4j, dulwich, spacy) AND a `pip-audit` CI gate to a future maintenance spec as follow-up work — that spec should cover the full dependency baseline AND continuous CVE monitoring as a single effort, since bundling them avoids two rounds of review and decision-making over the same files.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Hostile workspace ingest is contained (Priority: P1)

A user is asked to ingest a knowledge base they did not author — a shared notes repo, a vendor-supplied starter pack, a directory received from a third party. The workspace contains a symlink such as `notes/leak.md → /etc/passwd` or `notes/key.md → ~/.ssh/id_rsa`. The user runs `auditgraph ingest` and trusts that auditgraph will not read outside the workspace root.

**Why this priority**: Threat-model-complete: the local-first, single-user stance means every attack assumes the attacker cannot reach the workstation directly, only the files the user is persuaded to ingest. Symlink traversal breaks that containment. This is the highest-impact remaining finding after C1.

**Independent Test**: A test workspace with a symlink pointing outside the configured root runs through `auditgraph ingest` and `auditgraph import`. The resulting `.pkg/profiles/<profile>/` contains no artifact whose `source_path`, `text`, or any nested string field references the symlink's target content. The ingest run surfaces the symlink in its skip list with a dedicated reason so the user knows something was refused.

**Acceptance Scenarios**:

1. **Given** a workspace `demo/` containing `notes/leak.md` symlinked to `/tmp/outside/secret.txt`, **When** the user runs `auditgraph ingest --root demo`, **Then** the symlink is reported in the ingest manifest as skipped with a dedicated reason, no artifact anywhere under `demo/.pkg/` references the target's contents, and the run exits successfully.
2. **Given** the same workspace, **When** the user runs `auditgraph import demo/notes/`, **Then** the symlink is rejected with the same reason and no artifact referencing the target is written.
3. **Given** a workspace where the symlink target is a legitimate file *inside* the same workspace, **When** the user runs `auditgraph ingest`, **Then** the file is processed normally (legitimate intra-workspace symlinks are not collateral damage).

---

### User Story 2 — MCP tool calls are bounded by their declared contract (Priority: P1)

An LLM client is driving the auditgraph MCP server. The user has configured the server in read-only mode and expects that an adversarial or buggy LLM cannot cause writes outside the workspace, cannot flood the argv with injected flags, and cannot exceed declared parameter sizes.

**Why this priority**: The MCP server is the project's only LLM-facing trust boundary in practice (even though it uses stdio transport, the LLM input is adversarial by assumption). Today, the server accepts any JSON payload and forwards every key to the CLI as a flag, relying entirely on argparse downstream to reject unknown flags. That works today only because no CLI command happens to have a conflicting flag name. P1 alongside the symlink fix.

**Independent Test**: For every tool declared in `llm-tooling/tool.manifest.json`, submitting a payload with an unknown key, a value that exceeds a declared length cap, or a type that violates the declared `input_schema` is rejected before any subprocess is invoked.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** the client submits `{"unknown_key": "value"}` to any tool, **Then** the call is rejected with a contract-violation error and no subprocess is invoked.
2. **Given** a tool whose schema declares a string parameter, **When** the client submits an integer or object for that parameter, **Then** the call is rejected with a type-mismatch error.
3. **Given** a tool whose schema declares a string parameter, **When** the client submits a string exceeding the size cap, **Then** the call is rejected with a size-cap error.
4. **Given** the server is running in read-only mode, **When** a call would trigger any write path (including previously-bounded paths like `export --output`), **Then** the existing read-only enforcement path still engages.

---

### User Story 3 — Neo4j export path is contained within the workspace (Priority: P2)

A user runs `auditgraph export-neo4j --output <path>` and expects the output file to land inside the workspace (matching the behavior of the sister command `auditgraph export`). Today `export-neo4j` accepts arbitrary absolute paths, so a user who pastes a malicious command or whose LLM-assisted workflow supplies a wrong path can overwrite files anywhere the process has write permission.

**Why this priority**: Lower severity than stories 1-2 because `export-neo4j` is not currently exposed via MCP (only `export` is), so today's attack surface is limited to the user's own CLI invocations. Elevated to P2 so that future MCP additions cannot forget the containment check.

**Independent Test**: `auditgraph export-neo4j --output /tmp/attacker` (or any absolute path outside the workspace) is rejected with the same error shape that `auditgraph export --output <external>` already uses.

**Acceptance Scenarios**:

1. **Given** a workspace and a destination outside it, **When** the user runs `auditgraph export-neo4j --output /tmp/file.cypher`, **Then** the command fails with a containment error and no file is written.
2. **Given** a relative or workspace-relative `--output` path, **When** the user runs `auditgraph export-neo4j --output exports/neo4j/out.cypher`, **Then** the command succeeds and writes to the resolved workspace-relative location.
3. **Given** no `--output` flag, **When** the user runs `auditgraph export-neo4j`, **Then** the command writes to a deterministic default path under `<root>/exports/neo4j/`.

---

### User Story 4 — Redaction catches modern credential formats (Priority: P2)

A user ingests personal notes containing AWS access keys, Google API keys, OpenAI keys, Anthropic keys, Stripe live keys, GitHub fine-grained PATs, and variant credential keywords (`aws_access_key_id=`, `auth_token=`, `passwd=`). Today the detector allowlist misses all of these, so the Phase 1 C1 fix — which only scrubs what the detector set knows about — silently passes them through.

**Why this priority**: Medium. Phase 1 is load-bearing for the "auditgraph redacts credentials" promise; this story makes that promise deliver on 2026-era credential formats. P2 because the user has to actually ingest a credential in a vendor-specific format for the gap to matter.

**Independent Test**: A fixture document containing one instance of each format is ingested. Every shard under `.pkg/profiles/<profile>/` is walked and asserted to not contain any of the sentinel values.

**Acceptance Scenarios**:

1. **Given** a document containing `AKIAIOSFODNN7EXAMPLE`, an `AIza[...]` Google key, `sk-ant-api03-[...]`, `sk-proj-[...]`, `github_pat_[...]`, and a `xoxe.xoxp-[...]` Slack token, **When** the user runs `auditgraph ingest`, **Then** none of these values appear in any chunk, segment, document, or source artifact on disk.
2. **Given** a document containing `aws_access_key_id=ABC`, `auth_token=XYZ`, `passwd=123`, **When** the user runs `auditgraph ingest`, **Then** none of these values appear in any shard.
3. **Given** the `tests/test_redaction_detectors.py` suite, **When** the tests run, **Then** each new format has at least one positive test that the detector matches and at least one negative test that a visually-similar benign string does not match.

---

### User Story 5 — Cross-chunk PEM keys are fully redacted (Priority: P2)

A user ingests a document containing a real-shape RSA or ED25519 private key surrounded by prose. The key is long enough that when the text is chunked into 200-token windows, the `-----BEGIN PRIVATE KEY-----` header and the `-----END PRIVATE KEY-----` footer land in different chunks. Today the Phase 1 fix redacts each chunk in isolation, so the base64 body of the key survives in plaintext inside the chunk(s) that sit between the markers. The resolution (per Clarification Q1) is to move redaction upstream into the parser so the full document text is scrubbed once, before chunking begins — the cross-chunk PEM case becomes impossible by construction because there are no chunk boundaries yet when the detector runs.

**Why this priority**: Medium. Users who ingest PEM keys via notes are rare, but a single such ingest leaks the whole key because the attacker recovers the base64 body and can reconstruct the header themselves. P2, not P1, because Phase 1 + the detector expansion in User Story 4 already close the common credential-shaped-string case, and redact-before-chunk (Story 5) closes the remaining multi-line hole in a single architectural change.

**Independent Test**: Ingest a document with a real-shape 2048-bit RSA key padded with 2000 tokens of filler on each side so the key is guaranteed to straddle at least one chunk boundary at the default chunk size. Walk every chunk file under `.pkg/profiles/<profile>/chunks/` and assert that no chunk contains a contiguous base64-shaped run longer than 40 characters. Also verify, by reading the pipeline code, that the hotfix's post-chunking redaction pass has been removed and replaced by a single parser-level redaction call.

**Acceptance Scenarios**:

1. **Given** a document with a 2048-bit RSA PEM key and default chunk size 200 tokens, **When** the user runs `auditgraph ingest`, **Then** no chunk file contains any contiguous base64 substring longer than an agreed safe length (e.g., 40 characters of `[A-Za-z0-9+/=]`).
2. **Given** the same document, **When** the user runs `auditgraph ingest`, **Then** neither the `-----BEGIN-----` nor the `-----END-----` markers appear in any chunk, segment, or document shard (they must either both be replaced by a sentinel or both be absent).
3. **Given** a document where the entire PEM key fits inside a single chunk, **When** the user runs `auditgraph ingest`, **Then** the key is still redacted (regression guarantee for the in-chunk case that already works today).

---

### User Story 6 — Users can audit pre-hotfix `.pkg/` stores (Priority: P2)

A user upgraded auditgraph to a version that includes the Phase 1 C1 fix. Their existing `.pkg/profiles/default/` store was built before the fix and may contain cleartext credentials in `chunks/`. They want a command that audits the existing store and reports any detected credentials without requiring a full `auditgraph rebuild` first.

**Why this priority**: Medium. The Phase 1 CHANGELOG recommends `auditgraph rebuild` as the migration path, but a rebuild is a full pipeline re-run and some users may want a faster "am I poisoned?" signal. A `validate-store` command also gives users without the source files (e.g., after the originals were deleted) a way to know they have a problem at all.

**Independent Test**: A fixture `.pkg/` directory containing a chunk with an embedded sentinel is passed to `auditgraph validate-store`. The command exits with a non-zero status and reports the poisoned shard path and the matching detector category.

**Acceptance Scenarios**:

1. **Given** a `.pkg/` store containing at least one shard with a credential-shaped string, **When** the user runs `auditgraph validate-store --root <workspace>`, **Then** the command exits with a non-zero status, lists every poisoned shard path, and reports which detector category matched (without echoing the secret value).
2. **Given** a clean `.pkg/` store, **When** the user runs `auditgraph validate-store`, **Then** the command exits with a zero status and reports "no redaction misses detected".
3. **Given** a poisoned store, **When** the user runs `auditgraph rebuild` and then `auditgraph validate-store`, **Then** the second run exits with a zero status.

---

### User Story 7 — Remote Neo4j sync is warned about plaintext credentials (Priority: P3)

A user configures `auditgraph sync-neo4j` against a remote Neo4j instance using the `bolt://` (plaintext) scheme rather than `bolt+s://`. Today the connection succeeds silently and credentials traverse the network in cleartext.

**Why this priority**: Low. The local-first, single-user target user almost always hits `bolt://localhost:7687` where this doesn't matter. Users who point at a remote host are a small minority, but the failure mode (password on the wire) warrants a visible warning.

**Independent Test**: `NEO4J_URI=bolt://example.com:7687 auditgraph sync-neo4j --dry-run` emits a warning identifying the insecure scheme and suggesting `bolt+s://`.

**Acceptance Scenarios**:

1. **Given** `NEO4J_URI=bolt://localhost:7687`, **When** the user runs any Neo4j command, **Then** no warning is emitted (localhost loopback is safe).
2. **Given** `NEO4J_URI=bolt://remote.example.com:7687`, **When** the user runs any Neo4j command, **Then** a warning is emitted pointing at the insecure scheme and recommending `bolt+s://`.
3. **Given** `NEO4J_URI=bolt+s://remote.example.com:7687`, **When** the user runs any Neo4j command, **Then** no warning is emitted.

---

### User Story 8 — Pipeline postcondition prevents redaction regressions (Priority: P3)

A future change to the ingest pipeline (a new shard type, a new parser code path, a new metadata field) accidentally writes a credential to disk without routing it through the redactor. The Phase 1 fix catches the bug classes known today; this story catches the bug classes that don't exist yet.

**Why this priority**: Low — pure defense in depth. No current user is at risk from this story alone, but it makes the trust-boundary guarantee structurally self-enforcing so that a future regression surfaces at test time or run time rather than as a silent leak.

**Independent Test**: Manually inject a credential-shaped string into a freshly-written chunk file under a test `.pkg/`, then run the pipeline postcondition. The postcondition fails the run and identifies the offending shard.

**Acceptance Scenarios**:

1. **Given** a completed `auditgraph ingest` run on a clean workspace, **When** a test mutates a chunk file to re-inject `password=test_sentinel`, **Then** running the postcondition reports a redaction miss and fails with a dedicated status code.
2. **Given** a completed `auditgraph rebuild` run, **When** the postcondition runs automatically as the final pipeline step, **Then** it either confirms clean state or fails the run on any detected miss.
3. **Given** an ingest run that fails the postcondition, **When** the user retries with `--allow-redaction-misses`, **Then** the run completes with `status: tolerated` recorded in the manifest's `redaction_postcondition` entry and exit code zero, so the bypass is auditable but the operator can complete an emergency rebuild.

---

### Edge Cases

- **Symlink chains**: a symlink pointing to another symlink pointing to a file outside the workspace — must be resolved and refused at the final target, not the first hop.
- **Broken symlinks**: a symlink whose target does not exist — skipped with the same `symlink_refused` reason per FR-004, never crashes the run.
- **`--allow-symlinks` passed in Phase 2**: must raise `NotImplementedError` with a message pointing at the issue tracker; must NOT be silently accepted as a no-op (per FR-004a).
- **Case sensitivity**: detector regex must match both `Password=` and `password=` (currently handled by `(?i)` flag but must be explicitly regression-tested).
- **PEM key with trailing whitespace or Windows line endings**: the current detector requires specific markers; the Story 5 fix must catch both variants.
- **MCP tool with a schema that has legitimate `oneOf`/`anyOf` polymorphism**: validation must handle these without false rejections.
- **Validate-store on a workspace with no `.pkg/` yet**: should report "no store to validate" cleanly, not crash.
- **Validate-store on a store that contains binary chunks** (future-proofing for a potential binary parser): should skip binary content or decode before scanning, with the policy decided during clarify.
- **Bolt URI warning on a non-standard port or IPv6 literal for localhost**: the "is this localhost?" check must handle `127.0.0.1`, `::1`, and `localhost` consistently.
- **Postcondition on a very large workspace**: must complete in a bounded time relative to ingest — no scanning is permitted to double the pipeline wallclock.

## Requirements *(mandatory)*

### Functional Requirements

**Symlink containment (User Story 1)**

- **FR-001**: The system MUST refuse to ingest any file whose real path (after symlink resolution) falls outside the configured workspace root, for both `auditgraph ingest` and `auditgraph import`.
- **FR-002**: The system MUST surface refused symlinks in the ingest manifest with the dedicated, machine-readable reason `symlink_refused`. In addition, the system MUST emit a summary line to standard error at the end of the ingest run when at least one symlink was refused, of the form `WARN: refused N symlinks pointing outside <workspace_root> (see manifest for details)`. The stderr line MUST be emitted exactly once per run regardless of refused count, so it does not flood interactive sessions.
- **FR-003**: The system MUST treat intra-workspace symlinks (whose real path stays inside the workspace root) as legitimate and process them normally, so the containment check is not a blanket refusal of symlinks.
- **FR-004**: The system MUST resolve symlink chains fully before applying the containment check, so a multi-hop chain that ultimately escapes is still refused. Broken symlinks (whose target does not exist) MUST be skipped with the same `symlink_refused` reason rather than crashing the run.
- **FR-004a**: The CLI MUST recognize a `--allow-symlinks` flag on `auditgraph ingest` and `auditgraph import`, but in Phase 2 this flag MUST raise a `NotImplementedError` with a message pointing users at the issue tracker for use-case discussion. The flag is reserved for forward compatibility so a future spec can wire up legitimate cross-workspace symlink behavior without a CLI surface change. The flag MUST NOT be silently accepted as a no-op.

**MCP payload validation (User Story 2)**

- **FR-005**: The MCP server MUST validate every incoming tool-call payload against the target tool's declared `input_schema` before constructing any subprocess command, using a JSON Schema Draft 7-compatible validator. The chosen implementation is the `jsonschema` library (pinned `>=4,<5` in `pyproject.toml`).
- **FR-006**: The MCP server MUST reject payloads containing keys not declared in the tool's input schema (`additionalProperties: false` is enforced), even if the target CLI command would happen to accept an equivalent flag.
- **FR-007**: The MCP server MUST enforce a size cap on string parameter values via `maxLength` constraints declared per-parameter in the tool manifest. Parameters without an explicit `maxLength` MUST inherit a server-level default (proposed: 4096 characters) to bound the attack surface of argv construction and to protect against resource-exhaustion probes. The default MUST be configurable but MUST NOT be removable.
- **FR-008**: The MCP server MUST return a structured validation error of shape `{"error": {"code": "validation_failed", "tool": <name>, "field": <jsonpointer>, "reason": <message>}}` on rejection, and MUST NOT invoke the target command at all on validation failure. The error MUST NOT echo the rejected value to avoid reflecting attacker input back into operator logs.
- **FR-009**: The validation layer MUST be unit-tested against every tool declared in the tool manifest. Each tool gets at minimum three parametrized test cases: unknown-key payload, type-mismatched payload, and oversized-string payload. The test suite MUST fail if a new tool is added to the manifest without corresponding validation tests (enforced by an inventory check that compares manifest tool names against test parametrization).

**Export path containment (User Story 3)**

- **FR-010**: The `auditgraph export-neo4j` command MUST enforce the same workspace-containment check on its `--output` argument that `auditgraph export` already enforces.
- **FR-011**: When `--output` is omitted, `auditgraph export-neo4j` MUST write to a deterministic default path under the workspace root.

**Detector allowlist expansion (User Story 4)**

- **FR-012**: The redactor MUST detect and redact contemporary cloud provider credential formats: AWS access key IDs, Google API keys, Anthropic API keys, OpenAI API keys, Stripe live secret keys, GitHub fine-grained personal access tokens, and GitHub server/user/refresh tokens.
- **FR-013**: The redactor MUST detect and redact variant credential keywords in `key=value` / `key: value` shapes: `aws_access_key_id`, `aws_secret_access_key`, `auth_token`, `access_token`, `refresh_token`, `session_token`, `passwd`, `pwd`, `bearer`, `auth`.
- **FR-014**: The redactor MUST emit matches for AWS access key IDs, Google API keys, Anthropic API keys, OpenAI API keys, and Stripe live secret keys under a new `cloud_keys` summary category. GitHub tokens (including the new `github_pat_` and `gh[opsur]_` prefixes) and Slack tokens MUST remain under the existing `vendor_token` category. The two categories MUST appear as independent entries in the redaction summary so operators can distinguish cloud IAM credential leaks (high-blast-radius rotation) from developer platform token leaks (per-user rotation). The implementation choice between a single `cloud_keys` detector with alternation versus multiple sub-detectors sharing the `cloud_keys` category name is a plan-phase decision.
- **FR-015**: Every new detector added under this story MUST have at least one positive test and one negative test against a visually-similar benign string.

**Cross-chunk PEM redaction (User Story 5)**

- **FR-016**: The system MUST apply the full redactor detector set to raw document text *before* chunking, inside the parser entry point (`ingest/parsers.py:_build_document_metadata` or its planning-level successor), so that chunks inherit already-redacted text by construction. Multi-line secrets (PEM private keys, multi-line certificates, SSH key blocks, GPG blocks) MUST be caught in the single pre-chunking pass regardless of chunk size.
- **FR-017**: The system MUST remove the Phase 1 hotfix's post-chunking redaction pass (`pipeline/runner.py:run_ingest` and `run_import`) as part of the FR-016 change, so the ingest pipeline has a single canonical redaction call site per document. The Phase 1 shard-coverage regression tests (`test_ingest_redacts_body_credentials_across_all_shards`, `test_import_redacts_body_credentials_across_all_shards`) MUST continue to pass against the reorganized code path.
- **FR-018**: The redactor MUST continue to correctly redact PEM keys that fit in a single chunk and all single-line credential formats (regression guarantee for the Phase 1 behavior).

**Validate-store command (User Story 6)**

- **FR-019**: The system MUST expose an `auditgraph validate-store` command that scans the active profile's canonical shard directories (`entities/`, `chunks/`, `segments/`, `documents/`, `sources/`) under `.pkg/profiles/<profile>/` and reports any shards containing strings matching the current detector allowlist. The command MUST accept `--profile <name>` to override the active profile and `--all-profiles` to widen scope to every profile under `.pkg/profiles/*/`. The command MUST NOT scan `runs/` (pipeline manifests), `indexes/` (derived data), or `secrets/` (the redactor's own HMAC key).
- **FR-020**: The command MUST NOT echo the matched secret value in its output, only the file path (relative to the profile root) and the matching detector category. Output MUST include a per-profile summary when `--all-profiles` is in effect.
- **FR-021**: The command MUST exit with a non-zero status on any detected miss and a zero status on a clean store. Under `--all-profiles`, the exit code is non-zero if *any* scanned profile is poisoned, and the report identifies which profile(s). Workspaces with no `.pkg/profiles/` directory or with a `.pkg/` that contains no profile subdirectories MUST exit zero with the message `no store to validate`, not crash.
- **FR-022**: The command MUST NOT modify any on-disk artifact; it is strictly read-only. This includes not writing new run manifests, not updating indexes, and not rotating the redaction key.

**Plaintext Neo4j URI warning (User Story 7)**

- **FR-023**: The system MUST emit a visible warning to standard error when a Neo4j connection is established against a non-localhost host using the `bolt://` or `neo4j://` (unencrypted) URI schemes. The warning MUST name the host, identify the insecure scheme, and recommend the corresponding `bolt+s://` / `neo4j+s://` scheme.
- **FR-023a**: The system MUST support a `--require-tls` flag on both `auditgraph sync-neo4j` and `auditgraph export-neo4j` that escalates the warning to a hard refusal: non-localhost connections with an unencrypted scheme fail with a dedicated non-zero exit code (proposed: exit 4, distinct from generic errors at 1, argparse errors at 2, and redaction postcondition failures at 3). The environment variable `AUDITGRAPH_REQUIRE_TLS=1` MUST be honored as equivalent to the CLI flag so compliance-bound deployments can enforce strict mode without modifying every invocation.
- **FR-024**: The system MUST NOT emit a warning or trigger refusal for loopback hosts (`localhost`, `127.0.0.1`, `::1`) regardless of scheme, since loopback traffic is not network-exposed. The loopback check MUST handle all three canonical localhost forms consistently.

**Pipeline redaction postcondition (User Story 8)**

- **FR-025**: The `auditgraph rebuild` pipeline MUST run a redaction postcondition as its final step that walks every shard directory under the target profile and re-runs the detector set against every string field.
- **FR-026**: The postcondition MUST fail the run on any detected miss by default, exiting the process with a dedicated non-zero status code (proposed: exit 3, to distinguish from argparse errors at 2 and unhandled exceptions at 1). The manifest MUST record a structured `redaction_postcondition` entry with shape `{"status": "pass|fail|tolerated", "misses": [...], "allow_misses": bool}` identifying the offending shard(s) and detector category. The `misses` list MUST NOT echo the matched secret value, only the file path and detector category.
- **FR-027**: The system MUST provide a `--allow-redaction-misses` flag on `auditgraph rebuild` that completes the run with `status: tolerated` instead of failing, so operators can complete emergency rebuilds when the postcondition is blocking for a reason they cannot immediately fix. The flag name MUST be verbose enough to avoid accidental use in shell history and MUST be visible in the run manifest so the bypass decision is auditable.
- **FR-028**: The postcondition MUST complete in time proportional to the shard count and MUST NOT more than double the end-to-end rebuild wallclock compared to the pipeline without the postcondition.

**Dependency baseline (carried forward from NOTES Phase 4)**

- **FR-029**: The project MUST pin lower bounds for `pyyaml`, `pypdf`, and `python-docx` in `pyproject.toml` at or above the latest known-clean baseline established during the post-Spec-025 security audit. These three dependencies parse untrusted input (YAML config, PDFs, DOCX files from arbitrary workspaces) and a CVE in any of them is directly exploitable via `auditgraph ingest`. The specific version numbers and upper-bound policy are plan-phase decisions; the default MUST be "pin lower only, let pip resolve forward" unless a known upper-bound incompatibility exists.
- **FR-030**: The project MUST add `jsonschema>=4,<5` as a new runtime dependency in `pyproject.toml` (required by FR-005 for MCP payload validation). This is the only non-parser dependency added or modified by this spec.

### Key Entities

- **Redaction detector**: a named regex + category pairing that matches credential-shaped strings in document text. Existing categories include `jwt`, `bearer`, `credential`, `url_credential`, `vendor_token`, `pem_private_key`. This spec adds at least one new category (cloud keys) and extends one (credential keyword variants).
- **Workspace root**: the top-level directory the user passes via `--root` or `auditgraph init`. All path containment decisions in this spec refer to this directory's real (symlink-resolved) path.
- **Redaction postcondition manifest entry**: a new structured record inside the run manifest that reports the postcondition's pass/fail status and any misses.
- **Skip reason** (`symlink_refused`): a new machine-readable value added to the existing ingest-manifest skip-reason vocabulary.
- **Validation error**: the structured error shape returned by the MCP server on payload validation failure. Must include the tool name, the offending parameter, and a human-readable reason. Must NOT include the rejected value (to avoid reflecting attacker input back to attacker logs).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who ingests a hostile workspace with symlinks pointing outside the workspace root never sees the target files' contents reflected in any on-disk artifact under `.pkg/`. Coverage: every symlink in the Spec 027 fixture corpus.
- **SC-002**: Every tool declared in the MCP tool manifest is unit-tested to reject an unknown-key payload, a type-mismatched payload, and an oversized-string payload before any subprocess invocation. Coverage: 100% of tools listed in `tool.manifest.json`.
- **SC-003**: `auditgraph export-neo4j --output <external-absolute-path>` fails with the same containment-error shape as `auditgraph export --output <external-absolute-path>` — verified by a direct assertion in the test suite.
- **SC-004**: A test fixture document containing one instance of each credential format listed in FR-012 and FR-013 (11 distinct formats minimum) produces a `.pkg/` where no shard contains any of the sentinel values. The resulting redaction summary MUST show matches under both the `cloud_keys` and `vendor_token` categories (per FR-014), confirming that the severity-signal split is preserved. Coverage: 100% of the new format list.
- **SC-005**: The Spec 027 test corpus includes at least one PEM key case (2048-bit RSA minimum) that spans a chunk boundary at the default chunk size, and after ingest no chunk contains any contiguous base64-shaped run longer than 40 characters from the key body.
- **SC-006**: `auditgraph validate-store` on a fixture poisoned store exits non-zero and reports every poisoned shard; on a clean store it exits zero with no false positives; on a store that was just rebuilt from a poisoned source corpus it exits zero.
- **SC-007**: On a Neo4j URI targeting a non-localhost host with an unencrypted scheme, at least one visible warning is emitted to standard error during connection setup and the connection completes normally. With `--require-tls` (or `AUDITGRAPH_REQUIRE_TLS=1`), the same command refuses with a dedicated non-zero exit code and no connection is established. On a loopback host with any scheme, no warning is emitted and `--require-tls` does not block the connection.
- **SC-008**: The redaction postcondition catches a manual injection of `password=test_sentinel` into a freshly-written chunk file and fails the pipeline run with a dedicated status code. The postcondition's wallclock overhead on a 1000-file workspace is under 100% of the baseline rebuild time.
- **SC-009**: After all Phase 2-4 work ships, the full repository test suite runs in under 60 seconds on the reference developer machine (today: 27.5 seconds; ceiling allows headroom for the ~15 new test files this spec will generate).
- **SC-010**: A subsequent re-run of the aegis deep audit against the same repository reports zero findings at HIGH or CRITICAL severity for the categories covered by this spec (symlinks, MCP contract, export paths, redaction coverage, pipeline postcondition).

## Assumptions

- The Phase 1 C1 hotfix (commit `215398d`) is already on `main` and is not reopened by this spec.
- Users who have already ingested sensitive material before the Phase 1 hotfix may be relying on the new `validate-store` command (User Story 6) to audit their existing stores without a full rebuild.
- The project's constitutional non-negotiables (determinism, local-first, backwards compatibility, no co-author trailers) apply to every requirement in this spec — no Phase 2-4 deliverable may add network calls, introduce non-determinism, or break existing CLI invocations.
- `jsonschema` is an acceptable new runtime dependency for the MCP validation layer (User Story 2). If this turns out to be contentious, the open question during `/speckit.clarify` can revisit it — the manifest already uses jsonschema-flavored syntax, so a hand-rolled validator is a lower-preference fallback.
- The `PipelineRunner` god-class decomposition mentioned in NOTES Phase 4 is *not* in scope for this spec. It remains a separate engineering task because it is not a security finding per se and carries a much larger test-surface risk than the items above. It may be surfaced as a follow-up spec once Phase 2-4 stabilizes.
- **Follow-up maintenance spec (explicitly deferred from Clarification Q8)**: broader dependency pinning — `neo4j`, `dulwich`, `spacy`, and any transitive dependencies not addressed by FR-029 — plus a continuous `pip-audit` CI gate that fails on any new vulnerability in the pinned dependency set, MUST be captured as follow-up work in a separate maintenance spec. That future spec should bundle "pin everything" (Q8 option B) and "add pip-audit CI gate" (Q8 option D) into a single effort so the dependency baseline and continuous monitoring ship together. Spec 027 closes only the three parser deps because those are the ones where pinning is a *security* decision rather than routine hygiene; the rest belong in a dependency-hygiene spec that can batch them with other routine updates.

## Open questions to raise during `/speckit.clarify`

The following questions come directly from `specs/026-security-hardening/NOTES.md` "Open questions" plus new items surfaced by writing this spec. They are preserved here so the clarify pass has a ready-made agenda.

1. ~~**Symlink policy (FR-001)**: resolved by Clarification Q3 — skip with `symlink_refused` reason, single-line stderr warning at end of run, reserved `--allow-symlinks` flag that raises `NotImplementedError` in Phase 2.~~
2. ~~**M2 confirmation (User Story 5)**: resolved by Clarification Q1 — redact-before-chunk inside the parser, remove the hotfix's post-chunking pass.~~
3. ~~**Postcondition strictness (FR-026, FR-027)**: resolved by Clarification Q2 — fail by default with a `--allow-redaction-misses` opt-out flag, exit code 3 on unblocked failure.~~
4. ~~**Cloud-keys detector category (FR-014)**: resolved by Clarification Q6 — new `cloud_keys` category for AWS/GCP/OpenAI/Anthropic/Stripe; `vendor_token` stays narrow to GitHub/Slack developer tokens.~~
5. ~~**MCP validation dependency (FR-005)**: resolved by Clarification Q4 — `jsonschema` library, pinned `>=4,<5`.~~
6. ~~**Neo4j warning enforcement (FR-023)**: resolved by Clarification Q7 — warn by default, `--require-tls` flag plus `AUDITGRAPH_REQUIRE_TLS=1` env var for opt-in refusal with dedicated exit code 4.~~
7. ~~**Validate-store scope (FR-019)**: resolved by Clarification Q5 — active profile by default, canonical shards only, `--profile`/`--all-profiles` flags for scope override. `runs/`/`indexes/`/`secrets/` excluded.~~
8. ~~**Dependency pinning (FR-029, FR-030)**: resolved by Clarification Q8 — pin `pyyaml`, `pypdf`, `python-docx` in Spec 027 (direct exploit path via untrusted input). Broader pinning + `pip-audit` CI gate captured as a deferred follow-up maintenance spec in the Assumptions section.~~
