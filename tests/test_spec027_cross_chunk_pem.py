"""Spec 027 User Story 5 — cross-chunk PEM containment (M2 fix, FR-016..FR-018).

The hotfix from Spec 026 C1 redacted document/segment/chunk payloads
post-chunking, but that is too late for multi-line secrets: a PEM key
straddling a chunk boundary can survive the post-chunking pass intact
on the "wrong side" of the split. Phase 7 moves redaction to parser
entry so the full document text is scrubbed *before* chunking.

This test file verifies the behavior; T059's static check verifies the
hotfix's post-chunking code was actually removed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner


# 2048-bit RSA private keys contain ~1600 chars of base64 body. We emit a
# realistic header/footer and a long base64 body made of repeating filler
# so the whole block is long enough to straddle a 200-token chunk boundary
# even with generous filler prose on both sides.
PEM_BODY_LINES = [
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDfakeKeyDataFor",
    "TestingPurposesOnlyDoNotUseInProductionThisIsIntentionallyFake",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
] * 40  # ~120 lines of 64-char base64 → ~7680 chars total

FAKE_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    + "\n".join(PEM_BODY_LINES)
    + "\n-----END RSA PRIVATE KEY-----"
)

FILLER_TOKEN = "filler "
LONG_BASE64_RE = re.compile(r"[A-Za-z0-9+/=]{41,}")


def _walk_chunks(workspace: Path) -> list[dict]:
    pkg = workspace / ".pkg" / "profiles" / "default" / "chunks"
    if not pkg.exists():
        return []
    records = []
    for path in sorted(pkg.rglob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def _run_ingest(workspace: Path):
    runner = PipelineRunner()
    config = load_config(None)
    return runner.run_ingest(root=workspace, config=config)


def test_cross_chunk_pem_redacted(tmp_path: Path):
    """FR-016: PEM key straddling a chunk boundary must be fully redacted."""
    workspace = tmp_path / "workspace"
    notes = workspace / "notes"
    notes.mkdir(parents=True)

    # Surround the fake PEM with enough filler prose that the key definitely
    # crosses chunk boundaries (chunking is token-based at ~200 tokens).
    filler = FILLER_TOKEN * 2000
    content = f"# Notes\n\n{filler}\n\n{FAKE_PEM}\n\n{filler}\n"
    (notes / "leaky.md").write_text(content, encoding="utf-8")

    result = _run_ingest(workspace)
    assert result.status == "ok", f"ingest failed: {result}"

    chunks = _walk_chunks(workspace)
    assert chunks, "no chunks produced"

    for chunk in chunks:
        text = str(chunk.get("text", ""))
        # PEM header and footer must be gone
        assert "BEGIN RSA PRIVATE KEY" not in text, f"PEM header survived in chunk {chunk.get('chunk_id')}"
        assert "END RSA PRIVATE KEY" not in text
        # No contiguous base64-like run longer than 40 chars (research item R3).
        # Allow the redaction marker itself (it contains short hex digest).
        long_runs = LONG_BASE64_RE.findall(text)
        # The redaction marker `<<redacted:private_key:xxxxxxxxxxxx>>` contains
        # a 12-char hex digest — below 41 so won't match. Any remaining long
        # runs would indicate the PEM body survived chunking.
        assert not long_runs, (
            f"chunk {chunk.get('chunk_id')} still has long base64-like runs: {long_runs[:3]}"
        )


def test_in_chunk_pem_still_redacted(tmp_path: Path):
    """FR-018 regression guard: PEM keys that fit in one chunk must also be redacted."""
    workspace = tmp_path / "workspace"
    notes = workspace / "notes"
    notes.mkdir(parents=True)

    short_pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIBogIBAAJBALRiMLAHudeSA/x3h\n"
        "-----END RSA PRIVATE KEY-----"
    )
    (notes / "short.md").write_text(f"# Short\n\n{short_pem}\n", encoding="utf-8")

    result = _run_ingest(workspace)
    assert result.status == "ok"

    chunks = _walk_chunks(workspace)
    for chunk in chunks:
        text = str(chunk.get("text", ""))
        assert "BEGIN RSA PRIVATE KEY" not in text
        assert "MIIBogIBAAJBALRiMLAHudeSA" not in text
