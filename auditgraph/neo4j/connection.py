from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Neo4jConnectionProfile:
    uri: str
    user: str
    password: str
    database: str = "neo4j"
    max_connection_pool_size: int = 50


def load_connection_from_env(env: dict[str, str] | None = None) -> Neo4jConnectionProfile:
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
