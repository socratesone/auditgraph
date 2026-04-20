"""Spec 027 User Story 4 — credential_kv keyword expansion + new vendor prefixes.

Extends the `credential_kv` detector with modern credential keywords and
extends the `vendor_token` detector with new GitHub fine-grained PAT prefixes
plus the Slack `xoxe.xoxp-` format. FR-012..FR-014.
"""
from __future__ import annotations

import secrets

from auditgraph.utils.redaction import (
    RedactionPolicy,
    Redactor,
    _default_detectors,
)


KEY = secrets.token_bytes(32)


def _full_redactor() -> Redactor:
    detectors = tuple(_default_detectors().values())
    policy = RedactionPolicy(policy_id="test", version="v1", enabled=True, detectors=detectors)
    return Redactor(policy, KEY)


def _counts(result) -> dict:
    return dict(result.summary.counts_by_category)


def test_new_keyword_variants_detected():
    text = (
        "aws_access_key_id=ABC_SENTINEL_AKID\n"
        "auth_token=XYZ_SENTINEL_AUTH\n"
        "passwd=foo_SENTINEL_PWD\n"
        "refresh_token: bar_SENTINEL_REF\n"
        "bearer=baz_SENTINEL_BEAR\n"
        "auth=qux_SENTINEL_AUTHV\n"
    )
    result = _full_redactor().redact_text(text)
    for sentinel in (
        "ABC_SENTINEL_AKID",
        "XYZ_SENTINEL_AUTH",
        "foo_SENTINEL_PWD",
        "bar_SENTINEL_REF",
        "baz_SENTINEL_BEAR",
        "qux_SENTINEL_AUTHV",
    ):
        assert sentinel not in result.value, f"{sentinel} survived redaction"
    assert _counts(result).get("credential", 0) >= 6, f"got {_counts(result)}"


def test_existing_keywords_still_detected():
    """Regression guard: pre-Spec-027 keywords MUST still redact."""
    text = (
        "password=OLD_PWD_SENTINEL\n"
        "secret: OLD_SECRET_SENTINEL\n"
        "api_key=OLD_APIKEY_SENTINEL\n"
    )
    result = _full_redactor().redact_text(text)
    for sentinel in ("OLD_PWD_SENTINEL", "OLD_SECRET_SENTINEL", "OLD_APIKEY_SENTINEL"):
        assert sentinel not in result.value, f"{sentinel} survived (regression)"
    assert _counts(result).get("credential", 0) >= 3


def test_new_github_prefixes_in_vendor_token():
    tokens = {
        "github_pat": "github_pat_11ABCDEFG0abcdefghijkl_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "gho": "gho_AbCdEfGhIjKlMnOpQrSt",
        "ghu": "ghu_AbCdEfGhIjKlMnOpQrSt",
        "ghs": "ghs_AbCdEfGhIjKlMnOpQrSt",
        "ghr": "ghr_AbCdEfGhIjKlMnOpQrSt",
        "xoxe": "xoxe.xoxp-1-abcDEF1234567890",
    }
    text = "\n".join(f"{k}={v}" for k, v in tokens.items())
    result = _full_redactor().redact_text(text)
    for name, value in tokens.items():
        assert value not in result.value, f"{name} token {value!r} survived: {result.value!r}"
    assert _counts(result).get("vendor_token", 0) >= 6, f"got {_counts(result)}"
