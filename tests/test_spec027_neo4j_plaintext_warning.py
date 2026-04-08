"""Spec 027 User Story 7 — Neo4j plaintext URI warning + --require-tls (FR-023, FR-023a).

Non-localhost `bolt://` / `neo4j://` URIs emit a stderr warning. With
`--require-tls` (or `AUDITGRAPH_REQUIRE_TLS=1`), the warning is escalated
to a refusal with a dedicated exception (CLI exits 4). Loopback literals
are exempt regardless of strict mode and regardless of port.
"""
from __future__ import annotations

import pytest

from auditgraph.neo4j.connection import (
    Neo4jTlsRequiredError,
    _is_loopback_host,
    load_connection_from_env,
)


BASE_ENV = {
    "NEO4J_USER": "neo",
    "NEO4J_PASSWORD": "secret",
}


def _env(uri: str, **extra) -> dict:
    return {**BASE_ENV, "NEO4J_URI": uri, **extra}


def test_localhost_no_warning(capsys):
    load_connection_from_env(_env("bolt://localhost:7687"))
    captured = capsys.readouterr()
    assert "WARN" not in captured.err


def test_remote_plaintext_warns(capsys):
    load_connection_from_env(_env("bolt://example.com:7687"))
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "unencrypted" in captured.err.lower() or "plaintext" in captured.err.lower()
    assert "example.com" in captured.err


def test_remote_tls_no_warning(capsys):
    load_connection_from_env(_env("bolt+s://example.com:7687"))
    captured = capsys.readouterr()
    assert "WARN" not in captured.err


def test_require_tls_flag_refuses():
    with pytest.raises(Neo4jTlsRequiredError):
        load_connection_from_env(_env("bolt://example.com:7687"), require_tls=True)


def test_require_tls_env_var_refuses(monkeypatch):
    monkeypatch.setenv("AUDITGRAPH_REQUIRE_TLS", "1")
    with pytest.raises(Neo4jTlsRequiredError):
        load_connection_from_env(_env("bolt://example.com:7687"))


def test_localhost_require_tls_still_allowed():
    # Loopback exempts even under strict mode
    load_connection_from_env(_env("bolt://localhost:7687"), require_tls=True)


def test_ipv6_localhost_recognized(capsys):
    """Loopback check is host-only — non-standard ports stay loopback."""
    for uri in (
        "bolt://[::1]:7687",
        "bolt://127.0.0.1:7687",
        "bolt://localhost:17687",
    ):
        load_connection_from_env(_env(uri))
    captured = capsys.readouterr()
    assert "WARN" not in captured.err


def test_is_loopback_host_helper():
    assert _is_loopback_host("localhost")
    assert _is_loopback_host("LOCALHOST")
    assert _is_loopback_host("127.0.0.1")
    assert _is_loopback_host("::1")
    assert _is_loopback_host("[::1]")
    assert not _is_loopback_host("example.com")
    assert not _is_loopback_host("127.0.0.2")


# Helper for load_connection_from_env: support `require_tls` keyword.
# We patch the existing function signature in the implementation; the
# tests above already exercise the parameter form.
def _patch_signature_marker():
    import inspect
    sig = inspect.signature(load_connection_from_env)
    assert "require_tls" in sig.parameters, (
        "load_connection_from_env must accept require_tls keyword"
    )
