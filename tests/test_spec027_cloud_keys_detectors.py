"""Spec 027 User Story 4 — cloud_keys detector (FR-011..FR-015).

Adds a new `cloud_keys` category covering AWS / Google / Anthropic / OpenAI /
Stripe credentials. GitHub fine-grained PATs and `gh[opsur]_` / Slack `xoxe`
tokens live under the existing `vendor_token` category (Clarification Q6).
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


def test_aws_access_key_detected():
    text = "Some context AKIAIOSFODNN7EXAMPLE more text"
    result = _full_redactor().redact_text(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result.value
    assert _counts(result).get("cloud_keys", 0) >= 1


def test_google_api_key_detected():
    text = "key=AIzaSyD-EXAMPLE-ex4mpleKey-ABCDEFGHIJK1234 end"
    result = _full_redactor().redact_text(text)
    assert "AIzaSyD-EXAMPLE-ex4mpleKey-ABCDEFGHIJK1234" not in result.value
    assert _counts(result).get("cloud_keys", 0) >= 1


def test_anthropic_key_detected():
    text = "ANTHROPIC=sk-ant-api03-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXA_xyz end"
    result = _full_redactor().redact_text(text)
    assert "sk-ant-api03-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXA_xyz" not in result.value
    assert _counts(result).get("cloud_keys", 0) >= 1


def test_openai_key_detected():
    project_key = "sk-proj-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexample"
    # Legacy OpenAI format: sk- + 48-char alphanumeric body.
    legacy_body = "EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPL1"[:48]
    assert len(legacy_body) == 48
    legacy_key = f"sk-{legacy_body}"
    text = f"OPENAI_PROJECT={project_key}\nOPENAI_LEGACY={legacy_key}\n"
    result = _full_redactor().redact_text(text)
    assert project_key not in result.value
    assert legacy_key not in result.value
    assert _counts(result).get("cloud_keys", 0) >= 2


def test_stripe_key_detected():
    # Stripe live secret: sk_live_ + 24+ alphanumeric body.
    stripe_body = "EXAMPLEexampleEXAMPLEexa000"[:24]
    assert len(stripe_body) == 24
    stripe_key = f"sk_live_{stripe_body}"
    text = f"STRIPE={stripe_key} done"
    result = _full_redactor().redact_text(text)
    assert stripe_body not in result.value
    assert _counts(result).get("cloud_keys", 0) >= 1


def test_benign_strings_not_matched():
    """Negative test per FR-015 — these should NOT be redacted."""
    benign = [
        "my AKIA_planning notes",
        "sk-proj is a directory",
        "Mozilla/5.0 (AIza is not a key)",
    ]
    for text in benign:
        result = _full_redactor().redact_text(text)
        assert _counts(result).get("cloud_keys", 0) == 0, (
            f"benign string falsely matched cloud_keys: {text!r} -> {result.value!r}"
        )
        assert result.value == text, f"benign string was modified: {text!r} -> {result.value!r}"


def test_category_is_cloud_keys_not_vendor_token():
    """Verifies Clarification Q6: cloud_keys and vendor_token are distinct buckets."""
    text = (
        "aws=AKIAIOSFODNN7EXAMPLE\n"
        "gh=ghp_AbCdEfGhIjKlMnOpQrStUvWx1234567890\n"
    )
    result = _full_redactor().redact_text(text)
    counts = _counts(result)
    assert counts.get("cloud_keys", 0) == 1, f"expected cloud_keys=1, got {counts}"
    assert counts.get("vendor_token", 0) == 1, f"expected vendor_token=1, got {counts}"
