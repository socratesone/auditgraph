"""Tests for individual redaction detectors."""
from __future__ import annotations

import secrets

import pytest

from auditgraph.utils.redaction import (
    RedactionPolicy,
    RedactionSummary,
    Redactor,
    _apply_detector,
    _build_marker,
    _default_detectors,
)

KEY = secrets.token_bytes(32)


def _make_redactor(*detector_names: str) -> Redactor:
    """Build a Redactor with only the named detectors enabled."""
    all_detectors = _default_detectors()
    selected = tuple(all_detectors[n] for n in detector_names)
    policy = RedactionPolicy(
        policy_id="test", version="v1", enabled=True, detectors=selected
    )
    return Redactor(policy, KEY)


class TestPemPrivateKeyDetector:
    def test_pem_block_is_redacted(self) -> None:
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIBogIBAAJBALRiMLAHudeSA/x3h\n"
            "-----END RSA PRIVATE KEY-----"
        )
        redactor = _make_redactor("pem_private_key")
        result = redactor.redact_text(pem)
        assert "BEGIN RSA PRIVATE KEY" not in result.value
        assert "<<redacted:private_key:" in result.value
        assert result.summary.total_matches == 1

    def test_safe_text_unchanged(self) -> None:
        redactor = _make_redactor("pem_private_key")
        result = redactor.redact_text("just normal text")
        assert result.value == "just normal text"


class TestJwtDetector:
    def test_jwt_token_is_redacted(self) -> None:
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        redactor = _make_redactor("jwt")
        result = redactor.redact_text(f"token: {jwt}")
        assert jwt not in result.value
        assert "<<redacted:jwt:" in result.value
        assert result.summary.total_matches == 1


class TestBearerTokenDetector:
    def test_bearer_header_is_redacted(self) -> None:
        header = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tok.sig"
        redactor = _make_redactor("bearer_token")
        result = redactor.redact_text(header)
        # The token after "Bearer " should be replaced
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tok.sig" not in result.value
        assert "<<redacted:bearer:" in result.value
        assert result.summary.total_matches == 1

    def test_case_insensitive(self) -> None:
        header = "authorization: bearer mytoken123456"
        redactor = _make_redactor("bearer_token")
        result = redactor.redact_text(header)
        assert "mytoken123456" not in result.value
        assert "<<redacted:bearer:" in result.value
        assert result.summary.total_matches >= 1


class TestUrlCredentialsDetector:
    def test_url_password_is_redacted(self) -> None:
        url = "https://user:pass123secret@host.com/path"
        redactor = _make_redactor("url_credentials")
        result = redactor.redact_text(url)
        assert "pass123secret" not in result.value
        assert "<<redacted:url_credential:" in result.value
        assert result.summary.total_matches == 1


class TestVendorTokenDetector:
    def test_github_token_is_redacted(self) -> None:
        token = "ghp_AbCdEfGhIjKlMnOpQrStUvWx1234567890"
        redactor = _make_redactor("vendor_token")
        result = redactor.redact_text(f"token={token}")
        assert token not in result.value
        assert "<<redacted:vendor_token:" in result.value
        assert result.summary.total_matches == 1


class TestHmacStability:
    def test_same_secret_produces_same_marker(self) -> None:
        marker1 = _build_marker("test", "secret_value", KEY)
        marker2 = _build_marker("test", "secret_value", KEY)
        assert marker1 == marker2

    def test_different_secrets_produce_different_markers(self) -> None:
        marker1 = _build_marker("test", "secret_one", KEY)
        marker2 = _build_marker("test", "secret_two", KEY)
        assert marker1 != marker2

    def test_different_keys_produce_different_markers(self) -> None:
        key2 = secrets.token_bytes(32)
        marker1 = _build_marker("test", "same_secret", KEY)
        marker2 = _build_marker("test", "same_secret", key2)
        assert marker1 != marker2
