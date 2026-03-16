"""Extract sub-entities from markdown content.

Produces typed entities for:
- Headings (ag:section) — structural sections within a document
- Technologies (ag:technology) — known frameworks, languages, tools mentioned
- References (ag:reference) — markdown links and cross-references
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from auditgraph.storage.hashing import sha256_text
from auditgraph.storage.audit import DEFAULT_PIPELINE_VERSION

# Common technologies, frameworks, and tools to look for.
# Lowercase for matching; original case preserved in entity name.
_TECHNOLOGIES: dict[str, str] = {
    # Languages
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "rust": "Rust", "go": "Go", "java": "Java", "php": "PHP", "ruby": "Ruby",
    "bash": "Bash", "shell": "Shell", "html": "HTML", "css": "CSS", "sql": "SQL",
    "holy c": "Holy C", "c++": "C++",
    # Frameworks & libraries
    "react": "React", "angular": "Angular", "vue": "Vue", "next.js": "Next.js",
    "nextjs": "Next.js", "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "express": "Express", "node.js": "Node.js", "nodejs": "Node.js",
    "phaser": "Phaser", "three.js": "Three.js", "d3.js": "D3.js",
    "pyside6": "PySide6", "qt": "Qt", "vite": "Vite",
    # AI/ML
    "openai": "OpenAI", "anthropic": "Anthropic", "claude": "Claude",
    "langchain": "LangChain", "langgraph": "LangGraph",
    "spacy": "spaCy", "networkx": "NetworkX", "pytorch": "PyTorch",
    "tensorflow": "TensorFlow", "huggingface": "HuggingFace",
    "sentence-transformers": "Sentence-Transformers",
    "whisper": "Whisper", "deepgram": "Deepgram",
    # Databases & stores
    "neo4j": "Neo4j", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "redis": "Redis", "sqlite": "SQLite",
    "duckdb": "DuckDB", "janusgraph": "JanusGraph", "dgraph": "Dgraph",
    "chroma": "Chroma",
    # DevOps & tools
    "docker": "Docker", "kubernetes": "Kubernetes",
    "terraform": "Terraform", "github actions": "GitHub Actions",
    "playwright": "Playwright", "cypress": "Cypress", "jest": "Jest",
    "pytest": "pytest", "prometheus": "Prometheus",
    # Protocols & formats
    "mcp": "MCP", "graphql": "GraphQL", "rest": "REST",
    "rdf": "RDF", "sparql": "SPARQL", "json-rpc": "JSON-RPC",
    "websocket": "WebSocket", "sse": "SSE",
    # Data formats & libs
    "pydantic": "Pydantic", "sqlalchemy": "SQLAlchemy", "alembic": "Alembic",
    "rdflib": "RDFLib", "stripe": "Stripe",
}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# Word boundary pattern for technology matching — built once
_TECH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![A-Za-z])" + re.escape(key) + r"(?![A-Za-z])", re.IGNORECASE), canonical)
    for key, canonical in _TECHNOLOGIES.items()
]


def _entity_id(canonical_key: str) -> str:
    return f"ent_{sha256_text(canonical_key)}"


def extract_content_entities(
    source_path: str,
    source_hash: str,
    content: str,
) -> list[dict[str, Any]]:
    """Extract sub-entities from markdown content."""
    entities: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    # Extract headings as section entities
    for match in _HEADING_RE.finditer(content):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        line_no = content[:match.start()].count("\n") + 1
        canonical = f"section:{source_path}:{heading_text.lower().replace(' ', '_')}"
        if canonical in seen_keys:
            continue
        seen_keys.add(canonical)
        entities.append({
            "id": _entity_id(canonical),
            "type": "ag:section",
            "name": heading_text,
            "canonical_key": canonical,
            "aliases": [],
            "provenance": {
                "created_by_rule": "extract.content.heading.v1",
                "input_hash": source_hash,
                "pipeline_version": DEFAULT_PIPELINE_VERSION,
            },
            "refs": [{
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": line_no, "end_line": line_no},
            }],
            "metadata": {"heading_level": level},
        })

    # Extract technology mentions
    content_lower = content.lower()
    for pattern, canonical_name in _TECH_PATTERNS:
        match = pattern.search(content)
        if not match:
            continue
        canonical = f"tech:{canonical_name.lower().replace(' ', '_').replace('.', '_')}"
        if canonical in seen_keys:
            continue
        seen_keys.add(canonical)
        line_no = content[:match.start()].count("\n") + 1
        entities.append({
            "id": _entity_id(canonical),
            "type": "ag:technology",
            "name": canonical_name,
            "canonical_key": canonical,
            "aliases": [],
            "provenance": {
                "created_by_rule": "extract.content.technology.v1",
                "input_hash": source_hash,
                "pipeline_version": DEFAULT_PIPELINE_VERSION,
            },
            "refs": [{
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": line_no, "end_line": line_no},
            }],
        })

    # Extract markdown links as reference entities
    for match in _LINK_RE.finditer(content):
        link_text = match.group(1).strip()
        link_url = match.group(2).strip()
        if link_url.startswith("#"):
            continue  # Skip internal anchors
        line_no = content[:match.start()].count("\n") + 1
        canonical = f"ref:{source_path}:{sha256_text(link_url)[:16]}"
        if canonical in seen_keys:
            continue
        seen_keys.add(canonical)
        entities.append({
            "id": _entity_id(canonical),
            "type": "ag:reference",
            "name": link_text,
            "canonical_key": canonical,
            "aliases": [link_url],
            "provenance": {
                "created_by_rule": "extract.content.reference.v1",
                "input_hash": source_hash,
                "pipeline_version": DEFAULT_PIPELINE_VERSION,
            },
            "refs": [{
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": line_no, "end_line": line_no},
            }],
            "metadata": {"url": link_url},
        })

    return entities
