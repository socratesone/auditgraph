"""Spec-028 US2 · FR-015 + Invariant I2 redaction-in-subentities tests.

No entity or link record written to disk may contain a credential-shaped
string that passes any Spec-027 detector. The extractor re-applies the
Redactor to every emitted string as a defense-in-depth check (primary
redaction happens at parser entry per Spec-027 FR-016).
"""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from auditgraph.extract.markdown import DocumentsIndex, extract_markdown_subentities
from auditgraph.utils.redaction import RedactionPolicy, Redactor


FIXTURES = Path(__file__).parent / "fixtures" / "spec028"


def _scrubbing_redactor() -> Redactor:
    """A Redactor with all the Spec-027 detectors turned on."""
    from auditgraph.utils.redaction import _default_detectors

    detector_names = (
        "pem_private_key",
        "jwt",
        "bearer_token",
        "credential_kv",
        "url_credentials",
        "vendor_token",
    )
    registry = _default_detectors()
    detectors = tuple(registry[name] for name in detector_names if name in registry)
    return Redactor(
        RedactionPolicy(
            policy_id="test.all",
            version="v1",
            enabled=True,
            detectors=detectors,
        ),
        b"\x00" * 32,
    )


def _extract(text: str, redactor: Redactor, idx: DocumentsIndex):
    return extract_markdown_subentities(
        source_path="notes/with_secrets.md",
        source_hash="a" * 64,
        document_id="doc_test",
        document_anchor_id="ent_anchor",
        markdown_text=text,
        redactor=redactor,
        documents_index=idx,
        pipeline_version="v0.1.0",
    )


def test_secret_in_heading_is_redacted() -> None:
    """Section name MUST NOT contain a raw JWT even if the heading had one."""
    redactor = _scrubbing_redactor()
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = (FIXTURES / "with_secrets.md").read_text()
    entities, _ = _extract(text, redactor, idx)
    sections = [e for e in entities if e["type"] == "ag:section"]
    offending = [
        s for s in sections
        if "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123XYZ" in s["name"]
    ]
    assert offending == [], f"JWT leaked into section name: {offending}"


def test_secret_in_code_span_is_redacted() -> None:
    """An inline code span containing a key MUST NOT land unredacted on an ag:technology."""
    redactor = _scrubbing_redactor()
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = (FIXTURES / "with_secrets.md").read_text()
    entities, _ = _extract(text, redactor, idx)
    techs = [e for e in entities if e["type"] == "ag:technology"]
    offending = [
        t for t in techs
        if "sk-secret-1234567890abcdefghij1234" in t.get("canonical_key", "")
        or "sk-secret-1234567890abcdefghij1234" in t.get("name", "")
    ]
    assert offending == [], f"inline-code credential leaked: {offending}"


def test_secret_in_fence_info_does_not_cause_leak() -> None:
    """A fenced block with `yaml` info and secret body: body is not mined
    (FR-016g), so no technology entity carries the secret.
    """
    redactor = _scrubbing_redactor()
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = (FIXTURES / "with_secrets.md").read_text()
    entities, _ = _extract(text, redactor, idx)
    techs = [e for e in entities if e["type"] == "ag:technology"]
    # The fence info string is "yaml" — no secret there.
    for t in techs:
        assert "sk-fence-secret" not in t.get("canonical_key", "")
        assert "sk-fence-secret" not in t.get("name", "")


def test_secret_in_link_target_is_redacted() -> None:
    """A link href with URL credentials MUST be scrubbed on the ag:reference's target."""
    redactor = _scrubbing_redactor()
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = (FIXTURES / "with_secrets.md").read_text()
    entities, _ = _extract(text, redactor, idx)
    refs = [e for e in entities if e["type"] == "ag:reference"]
    # Some reference targeted https://user:supersecret@example.com/...
    for ref in refs:
        assert "supersecret" not in ref.get("target", "")
        assert "supersecret" not in ref.get("canonical_key", "")


def test_invariant_i2_no_credential_leaks_any_string_field() -> None:
    """Any emitted string field must be free of raw secrets from the fixture."""
    redactor = _scrubbing_redactor()
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = (FIXTURES / "with_secrets.md").read_text()
    entities, links = _extract(text, redactor, idx)

    forbidden = [
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123XYZ",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.def456XYZ",
        "sk-secret-1234567890abcdefghij1234",
        "sk-fence-secret-0987654321abcdefghij1234",
        "supersecret",
    ]

    import json as _json

    for entity in entities:
        blob = _json.dumps(entity)
        for bad in forbidden:
            assert bad not in blob, f"I2 violated: {bad!r} leaked into entity {entity.get('id')}"
    for link in links:
        blob = _json.dumps(link)
        for bad in forbidden:
            assert bad not in blob, f"I2 violated: {bad!r} leaked into link {link.get('id')}"
