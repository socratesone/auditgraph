from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_PLAINTEXT_SCHEMES = frozenset({"bolt", "neo4j"})


class Neo4jTlsRequiredError(RuntimeError):
    """Raised when --require-tls is in effect and a plaintext non-loopback
    Neo4j URI is presented. Spec 027 FR-023a."""


@dataclass(frozen=True)
class Neo4jConnectionProfile:
    uri: str
    user: str
    password: str
    database: str = "neo4j"
    max_connection_pool_size: int = 50


def _is_loopback_host(host: str) -> bool:
    """Return True if ``host`` is a loopback literal.

    Strips IPv6 brackets and lowercases. Port-independent — the caller
    must pass only the host portion (no `:port` suffix).
    """
    if not host:
        return False
    h = host.strip().lower()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    return h in _LOOPBACK_HOSTS


def _parse_host_and_scheme(uri: str) -> tuple[str, str]:
    """Parse ``uri`` and return ``(scheme_lower, host_lower)``.

    Handles IPv6 hosts via the standard urlparse path. The returned host
    excludes port and brackets."""
    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    return scheme, host


def load_connection_from_env(
    env: dict[str, str] | None = None,
    *,
    require_tls: bool | None = None,
) -> Neo4jConnectionProfile:
    """Build a `Neo4jConnectionProfile` from environment variables.

    Spec 027 FR-023: a non-loopback `bolt://`/`neo4j://` URI emits a
    one-line stderr warning. With ``require_tls=True`` (or
    ``AUDITGRAPH_REQUIRE_TLS=1`` in the environment), the warning is
    promoted to a `Neo4jTlsRequiredError` and the function raises before
    constructing the profile.
    """
    mapping = env if env is not None else os.environ
    uri = str(mapping.get("NEO4J_URI", "")).strip()
    user = str(mapping.get("NEO4J_USER", "")).strip()
    password = str(mapping.get("NEO4J_PASSWORD", "")).strip()
    database = str(mapping.get("NEO4J_DATABASE", "neo4j")).strip() or "neo4j"

    if not uri:
        raise ValueError("Missing environment variable: NEO4J_URI")
    if not user:
        raise ValueError("Missing environment variable: NEO4J_USER")
    if not password:
        raise ValueError("Missing environment variable: NEO4J_PASSWORD")
    if not uri.startswith(("bolt://", "neo4j://", "bolt+s://", "neo4j+s://")):
        raise ValueError("Invalid NEO4J_URI scheme; expected bolt:// or neo4j://")

    scheme, host = _parse_host_and_scheme(uri)
    if scheme in _PLAINTEXT_SCHEMES and not _is_loopback_host(host):
        # Spec 027 FR-023 / FR-023a
        strict = require_tls
        if strict is None:
            # Always consult os.environ for the strict flag — it is a
            # process-level policy switch, not a per-call config option.
            strict = (
                mapping.get("AUDITGRAPH_REQUIRE_TLS") == "1"
                or os.environ.get("AUDITGRAPH_REQUIRE_TLS") == "1"
            )
        if strict:
            raise Neo4jTlsRequiredError(
                f"Neo4j URI uses unencrypted scheme '{scheme}://' against non-loopback "
                f"host {host} and AUDITGRAPH_REQUIRE_TLS / --require-tls is set. "
                f"Use bolt+s:// or neo4j+s:// instead."
            )
        sys.stderr.write(
            f"WARN: Neo4j URI uses unencrypted scheme '{scheme}://' against non-localhost "
            f"host {host}; credentials will be transmitted in plaintext. "
            f"Use bolt+s:// or neo4j+s:// to encrypt.\n"
        )

    return Neo4jConnectionProfile(uri=uri, user=user, password=password, database=database)


def create_driver(profile: Neo4jConnectionProfile) -> Any:
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("neo4j driver not installed; install package 'neo4j'") from exc
    return GraphDatabase.driver(
        profile.uri,
        auth=(profile.user, profile.password),
        max_connection_pool_size=profile.max_connection_pool_size,
    )


def ping_connection(driver: Any, database: str) -> None:
    with driver.session(database=database) as session:
        session.run("RETURN 1 AS ok")


def map_neo4j_exception(exc: Exception) -> str:
    message = str(exc)
    cls_name = exc.__class__.__name__
    if cls_name in {"ServiceUnavailable", "ConnectionError"}:
        return f"Neo4j connection failed. Check NEO4J_URI and network reachability. Details: {message}"
    if cls_name in {"AuthError", "Unauthorized"}:
        return f"Neo4j authentication failed. Verify NEO4J_USER and NEO4J_PASSWORD. Details: {message}"
    if cls_name in {"TransientError"}:
        return f"Neo4j transient transaction error. Retry may succeed. Details: {message}"
    if cls_name in {"ClientError"}:
        return f"Neo4j client/query error during sync. Verify constraints and Cypher statements. Details: {message}"
    return f"Neo4j sync failed: {message}"
