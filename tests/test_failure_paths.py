"""Failure-path tests for redaction edge cases and corrupted document handling."""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.ingest.parsers import parse_file
from auditgraph.ingest.policy import load_policy
from auditgraph.utils.redaction import (
    RedactionPolicy,
    Redactor,
    _default_detectors,
)

KEY = secrets.token_bytes(32)


def _make_redactor(*detector_names: str) -> Redactor:
    all_detectors = _default_detectors()
    selected = tuple(all_detectors[n] for n in detector_names)
    policy = RedactionPolicy(
        policy_id="test", version="v1", enabled=True, detectors=selected
    )
    return Redactor(policy, KEY)


def _null_redactor_options() -> dict:
    """Spec 027 FR-016: parse_file requires a redactor in options."""
    policy = RedactionPolicy(
        policy_id="test.null.v1", version="v1", enabled=True, detectors=()
    )
    return {"redactor": Redactor(policy, KEY)}


class TestTruncatedPemBlock:
    def test_truncated_pem_not_redacted(self) -> None:
        """A PEM block missing the END marker is NOT matched by the detector.

        This documents a known gap: truncated PEM blocks leak through.
        The detector uses a DOTALL regex requiring both BEGIN and END.
        """
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIBogIBAAJBALRiMLAHudeSA/x3h\n"
            # missing END marker
        )
        redactor = _make_redactor("pem_private_key")
        result = redactor.redact_text(pem)
        # Documents current behavior: truncated block is NOT caught
        assert "BEGIN RSA PRIVATE KEY" in result.value
        assert result.summary.total_matches == 0


class TestMalformedJwt:
    def test_two_segment_string_not_matched(self) -> None:
        """A dot-separated string with only 2 segments should not be redacted as JWT."""
        text = "not.a.jwt but eyJhbGciOiJIUzI.eyJzdWIiOiJ1c2VyIn0"
        redactor = _make_redactor("jwt")
        result = redactor.redact_text(text)
        assert result.summary.counts_by_category.get("jwt", 0) == 0

    def test_short_segments_not_matched(self) -> None:
        """Dot-separated strings with short segments should not match JWT pattern."""
        text = "v0.1.0 and extract.note.v1 are not JWTs"
        redactor = _make_redactor("jwt")
        result = redactor.redact_text(text)
        assert result.summary.total_matches == 0
        assert result.value == text


class TestCorruptedDocumentHandling:
    def test_corrupted_pdf_fails_gracefully(self, tmp_path: Path) -> None:
        """Corrupted PDF bytes produce a failed ParseResult, not a crash."""
        bad_pdf = tmp_path / "corrupted.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4 corrupted garbage data here")
        policy = load_policy(load_config(None).profile())

        result = parse_file(bad_pdf, policy, _null_redactor_options())

        assert result.status == "failed"
        assert result.parser_id == "document/pdf"
        assert isinstance(result.status_reason, str)
        assert len(result.status_reason) > 0

    def test_empty_pdf_fails_gracefully(self, tmp_path: Path) -> None:
        """An empty .pdf file produces a failed ParseResult."""
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")
        policy = load_policy(load_config(None).profile())

        result = parse_file(empty_pdf, policy, _null_redactor_options())

        assert result.status == "failed"
        assert result.parser_id == "document/pdf"

    def test_corrupted_docx_fails_gracefully(self, tmp_path: Path) -> None:
        """Corrupted .docx bytes produce a failed ParseResult, not a crash."""
        bad_docx = tmp_path / "corrupted.docx"
        bad_docx.write_bytes(b"PK\x03\x04 not a real zip archive")
        policy = load_policy(load_config(None).profile())

        result = parse_file(bad_docx, policy, _null_redactor_options())

        assert result.status == "failed"
        assert result.parser_id == "document/docx"
        assert isinstance(result.status_reason, str)
