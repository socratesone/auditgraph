# Quickstart — Spec 027 Security Hardening

Linear walkthrough that exercises every Phase 2-4 deliverable in a realistic sequence. Doubles as the acceptance-test narrative: each numbered step maps to one user story and at least one test file.

**Assumes**: A development venv with the Spec 027 changes applied, `auditgraph` installed via `pip install -e .`, and `jsonschema>=4` pulled in by the updated `pyproject.toml`.

---

## 0. Baseline: confirm the install

```bash
source .venv/bin/activate
auditgraph version
python -c "import jsonschema; print('jsonschema', jsonschema.__version__)"
pytest tests/test_spec011_*.py tests/test_spec027_*.py -v
```

Expected: `auditgraph version` returns v0.1.0 (or current), jsonschema prints `>=4.0.0 <5`, all Spec 011 + Spec 027 tests pass.

---

## 1. Hostile workspace ingest is contained (User Story 1, FR-001–FR-004a)

Create a workspace containing an escaping symlink and confirm the ingest refuses it with a manifest skip reason and a stderr warning.

```bash
# Setup
mkdir -p /tmp/sp027-demo/notes
echo "# Clean note" > /tmp/sp027-demo/notes/clean.md

# Create an escaping symlink to a file outside the workspace
mkdir -p /tmp/sp027-outside
echo "outside content" > /tmp/sp027-outside/secret.txt
ln -sf /tmp/sp027-outside/secret.txt /tmp/sp027-demo/notes/leak.md

# Initialize and ingest
cd /tmp/sp027-demo
auditgraph init --root .
auditgraph ingest --root . 2>stderr.log

# Verify the refusal
cat stderr.log
# Expected: "WARN: refused 1 symlinks pointing outside /tmp/sp027-demo (see manifest for details)"

# Verify the manifest
find .pkg -name 'ingest-manifest.json' -exec grep -l symlink_refused {} \;
# Expected: at least one manifest contains "symlink_refused"

# Verify the target's contents never reached the store
grep -r "outside content" .pkg/ && echo "LEAK" || echo "clean"
# Expected: "clean"
```

Maps to: `tests/test_spec027_symlink_containment.py`. FR-001, FR-002, FR-003, FR-004.

---

## 2. `--allow-symlinks` is reserved but not implemented (FR-004a)

Confirm that passing the reserved flag does not silently accept the escape.

```bash
auditgraph ingest --root /tmp/sp027-demo --allow-symlinks
# Expected: process exits with a NotImplementedError referencing the issue tracker.
# MUST NOT silently ingest the symlink target.
```

Maps to: `tests/test_spec027_symlink_containment.py::test_allow_symlinks_flag_raises`. FR-004a.

---

## 3. MCP payload validation rejects bad inputs (User Story 2, FR-005–FR-009)

Exercise the new `jsonschema`-backed validator directly by submitting adversarial payloads to `execute_tool`.

```python
# tests/test_spec027_mcp_payload_validation.py-style invocation
from llm_tooling.mcp.server import execute_tool

# Unknown key
result = execute_tool("ag_query", {"q": "hello", "__injected__": "value"})
assert result["error"]["code"] == "validation_failed"
assert result["error"]["reason"].startswith("unknown property")

# Type mismatch
result = execute_tool("ag_query", {"q": 42})
assert result["error"]["code"] == "validation_failed"
assert "expected string" in result["error"]["reason"]
assert result["error"]["reason"] != "expected string, got 42"   # instance never echoed

# Oversized string
result = execute_tool("ag_query", {"q": "A" * 5000})
assert result["error"]["code"] == "validation_failed"
assert "exceeds maxLength" in result["error"]["reason"]

# Positive case: a well-formed payload still passes through
result = execute_tool("ag_version", {})
assert "error" not in result
```

Maps to: `tests/test_spec027_mcp_payload_validation.py`. FR-005, FR-006, FR-007, FR-008, FR-009.

---

## 4. `export-neo4j --output` is contained (User Story 3, FR-010, FR-011)

Confirm that the sister command now enforces the same path containment check as `export`.

```bash
cd /tmp/sp027-demo
auditgraph rebuild --root .   # build a minimal store first

# External output path must be refused
auditgraph export-neo4j --root . --output /tmp/attacker.cypher
# Expected: non-zero exit with "path must remain within" error.

# Workspace-relative output path still works
auditgraph export-neo4j --root . --output exports/neo4j/my.cypher
# Expected: exit 0, file created at .../exports/neo4j/my.cypher

# Default path when --output omitted
auditgraph export-neo4j --root .
# Expected: exit 0, file created at .../exports/neo4j/export.cypher
```

Maps to: `tests/test_spec027_export_neo4j_containment.py`. FR-010, FR-011.

---

## 5. Expanded detector catches modern cloud credentials (User Story 4, FR-012–FR-015)

Create a note containing one instance of each new credential format, ingest it, and confirm every sentinel is scrubbed from every shard.

```bash
cat > /tmp/sp027-demo/notes/creds.md <<'EOF'
# Credential test

AWS: AKIAIOSFODNN7EXAMPLE
Google: AIzaSyD-EXAMPLE-ex4mpleKey-ABCDEFGHIJK1234
Anthropic: sk-ant-api03-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXA_xyz
OpenAI: sk-proj-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexample
Stripe: sk_live_EXAMPLEexampleEXAMPLEex
GitHub fine: github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz0123456789ABCD
Slack new: xoxe.xoxp-1-abcdefg0123456789

aws_access_key_id=AKIA1111111111111111
auth_token=xyz789
passwd=hunter2
EOF

auditgraph rebuild --root .

# Confirm NONE of the sentinels survive in any shard
for sentinel in AKIAIOSFODNN7EXAMPLE AIzaSyD ak-ant-api03 sk-proj sk_live_EXAMPLE github_pat_11 xoxe.xoxp auth_token=xyz; do
  echo -n "$sentinel: "
  if grep -rq "$sentinel" .pkg/profiles/default/chunks .pkg/profiles/default/segments .pkg/profiles/default/documents; then
    echo "LEAK"
  else
    echo "clean"
  fi
done
# Expected: all "clean"

# Confirm the redaction summary shows BOTH cloud_keys AND vendor_token categories
auditgraph list --type source --format json | jq '.[] | .redaction_summary'
# Expected: by_category contains both "cloud_keys" and "vendor_token" with non-zero counts
```

Maps to: `tests/test_spec027_cloud_keys_detectors.py`, `tests/test_spec027_credential_kv_variants.py`. FR-012, FR-013, FR-014, FR-015.

---

## 6. Cross-chunk PEM keys are fully redacted (User Story 5, FR-016–FR-018)

Create a document large enough to force a PEM key across a chunk boundary, ingest it, and confirm no base64 run longer than 40 characters survives.

```python
# tests/test_spec027_cross_chunk_pem.py-style setup
from pathlib import Path
import re

PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEpAIBAAKCAQEAxxxx" * 60 + "\n"   # ~1200 chars of fake body, similar shape to real RSA 2048
    "-----END RSA PRIVATE KEY-----\n"
)
FILLER = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 200   # ~11200 chars
doc = FILLER + "\n\n" + PEM + "\n\n" + FILLER

# Write the document and ingest it
Path("/tmp/sp027-demo/notes/pem.md").write_text(doc)
# ... run auditgraph rebuild ...

# Walk every chunk file and assert no chunk contains a continuous base64-shaped run > 40 chars
BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{41,}")
for chunk_file in Path("/tmp/sp027-demo/.pkg/profiles/default/chunks").rglob("*.json"):
    content = chunk_file.read_text()
    assert not BASE64_RUN.search(content), f"base64 run > 40 chars survived in {chunk_file}"
assert True   # If we got here, all chunks are clean
```

Also confirm the fix is in the right place by reading `auditgraph/pipeline/runner.py` and verifying the hotfix's post-chunking `redactor.redact_payload(...)` calls have been removed, replaced by a single pre-chunking redaction inside `_build_document_metadata`.

Maps to: `tests/test_spec027_cross_chunk_pem.py`, `tests/test_spec027_parser_redaction.py`. FR-016, FR-017, FR-018.

---

## 7. `auditgraph validate-store` audits an existing store (User Story 6, FR-019–FR-022)

Use the new command to audit the workspace built by steps 1-6 and confirm it exits zero.

```bash
# On the clean store built by the walkthrough so far
auditgraph validate-store --root /tmp/sp027-demo
# Expected: exit 0, output "No redaction misses detected. Scanned: N shards across 1 profile(s) in Nms."

# Simulate a poisoned store by manually injecting a credential into an existing chunk
CHUNK=$(find /tmp/sp027-demo/.pkg/profiles/default/chunks -name '*.json' | head -1)
python -c "
import json, sys
p = '$CHUNK'
d = json.load(open(p))
d['text'] += ' password=INJECTED_SENTINEL_XYZ'
json.dump(d, open(p, 'w'))
"

# Now validate-store must fail
auditgraph validate-store --root /tmp/sp027-demo
# Expected: exit 1, report lists $CHUNK with category `credential` in field `text`.
# Expected: output does NOT contain the literal string "INJECTED_SENTINEL_XYZ".

# --all-profiles scans every profile
auditgraph validate-store --root /tmp/sp027-demo --all-profiles --format json | jq .
# Expected: json shape with `profiles` dict and `poisoned_profiles: ["default"]`

# A workspace with no .pkg yet exits zero with "no store to validate"
mkdir /tmp/sp027-empty
auditgraph validate-store --root /tmp/sp027-empty
# Expected: exit 0, "no store to validate"
```

Maps to: `tests/test_spec027_validate_store.py`. FR-019, FR-020, FR-021, FR-022.

---

## 8. Neo4j plaintext URI warns (FR-023, FR-024) and `--require-tls` refuses (FR-023a)

Confirm that the Neo4j connection layer warns on non-localhost plaintext URIs and refuses when strict mode is enabled.

```bash
# Loopback: no warning, no refusal, either mode
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=test \
  auditgraph sync-neo4j --dry-run --root /tmp/sp027-demo 2>stderr.log
grep WARN stderr.log
# Expected: no output (no warning on loopback)

# Remote plaintext: warns but proceeds
NEO4J_URI=bolt://example.com:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=test \
  auditgraph sync-neo4j --dry-run --root /tmp/sp027-demo 2>stderr.log
grep WARN stderr.log
# Expected: "WARN: Neo4j URI uses unencrypted scheme against non-localhost host example.com..."

# Remote plaintext + --require-tls: refuses with exit 4
NEO4J_URI=bolt://example.com:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=test \
  auditgraph sync-neo4j --dry-run --require-tls --root /tmp/sp027-demo
echo "exit=$?"
# Expected: exit=4

# Same refusal via env var
NEO4J_URI=bolt://example.com:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=test AUDITGRAPH_REQUIRE_TLS=1 \
  auditgraph sync-neo4j --dry-run --root /tmp/sp027-demo
echo "exit=$?"
# Expected: exit=4

# Remote TLS: no warning, no refusal
NEO4J_URI=bolt+s://example.com:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=test \
  auditgraph sync-neo4j --dry-run --require-tls --root /tmp/sp027-demo 2>stderr.log
grep WARN stderr.log
# Expected: no output
```

Maps to: `tests/test_spec027_neo4j_plaintext_warning.py`. FR-023, FR-023a, FR-024.

---

## 9. Redaction postcondition blocks dirty rebuilds (User Story 8, FR-025–FR-028)

Confirm the pipeline postcondition catches manually-injected misses and respects the `--allow-redaction-misses` opt-out.

```bash
# Step 7 already injected a miss. A new rebuild MUST fail with exit 3.
auditgraph rebuild --root /tmp/sp027-demo
echo "exit=$?"
# Expected: exit=3
# Note: the rebuild may regenerate the chunk from the clean source, wiping the miss.
# The test version of this step uses a fresher injection + a mocked source that can't be rebuilt.

# Confirm the manifest records the fail
find /tmp/sp027-demo/.pkg -name 'index-manifest.json' -exec jq '.redaction_postcondition' {} \;
# Expected: {"status": "fail", "misses": [...], "allow_misses": false, ...}

# With --allow-redaction-misses, the rebuild completes
auditgraph rebuild --root /tmp/sp027-demo --allow-redaction-misses
echo "exit=$?"
# Expected: exit=0
# Manifest records status: "tolerated", allow_misses: true
```

For a cleaner test flow, use a fixture that mutates a chunk AFTER rebuild (so the postcondition catches it on a subsequent scan):

```python
# tests/test_spec027_postcondition.py-style setup
# 1. Run auditgraph rebuild on a clean workspace (postcondition passes)
# 2. Manually mutate a chunk file on disk
# 3. Invoke the postcondition directly (not via full rebuild) and assert it fails
```

Maps to: `tests/test_spec027_postcondition.py`, `tests/test_spec027_postcondition_manifest.py`. FR-025, FR-026, FR-027, FR-028.

---

## 10. Dependency baseline check (FR-029, FR-030)

Confirm `pyproject.toml` pins the parser libraries and the new `jsonschema` dependency.

```bash
grep -E '"(pyyaml|pypdf|python-docx|jsonschema)' pyproject.toml
# Expected:
#   "pyyaml>=6.0.3",
#   "pypdf>=6.9.1",
#   "python-docx>=1.2.0",
#   "jsonschema>=4,<5",

# Confirm a fresh install resolves to these versions or newer
pip install -e . --upgrade --dry-run
# Expected: pyyaml, pypdf, python-docx, jsonschema all satisfy the pins
```

Maps to: `tests/test_spec027_dependency_baseline.py`. FR-029, FR-030.

---

## 11. Full suite green check

```bash
pytest tests/ -q
# Expected: all tests pass in under 60 seconds (SC-009)
```

---

## 12. Re-run the audit (SC-010)

Once every step above passes, re-run the aegis deep audit against the same categories that Spec 027 addresses (symlinks, MCP contract, export paths, redaction coverage, pipeline postcondition). Expected: **zero findings at HIGH or CRITICAL severity** for those categories. Any residual findings go into a new pre-spec NOTES document for a future spec cycle.

---

## Mapping: steps → user stories → tests

| Step | User story | Test file |
|---|---|---|
| 1, 2 | US1 symlink containment | `test_spec027_symlink_containment.py` |
| 3 | US2 MCP validation | `test_spec027_mcp_payload_validation.py` |
| 4 | US3 export-neo4j path | `test_spec027_export_neo4j_containment.py` |
| 5 | US4 cloud keys + kv variants | `test_spec027_cloud_keys_detectors.py`, `test_spec027_credential_kv_variants.py` |
| 6 | US5 cross-chunk PEM + parser redaction | `test_spec027_cross_chunk_pem.py`, `test_spec027_parser_redaction.py` |
| 7 | US6 validate-store | `test_spec027_validate_store.py` |
| 8 | US7 Neo4j warning + require-tls | `test_spec027_neo4j_plaintext_warning.py` |
| 9 | US8 postcondition | `test_spec027_postcondition.py`, `test_spec027_postcondition_manifest.py` |
| 10 | FR-029/030 dependency baseline | `test_spec027_dependency_baseline.py` |
| 11 | SC-009 full suite green | (all of the above, plus every other test in `tests/`) |
| 12 | SC-010 re-audit | (external, not a pytest file) |
