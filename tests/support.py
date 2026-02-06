from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.extract.entities import build_entity
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import sha256_text


def pkg_root(root: Path) -> Path:
    return profile_pkg_root(root, load_config(None))


def make_entity(name: str, source_path: str) -> dict[str, object]:
    source_hash = sha256_text(f"{name}:{source_path}")
    return build_entity(
        {
            "type": "file",
            "name": name,
            "canonical_key": f"file:{source_path}",
            "source_path": source_path,
        },
        source_hash,
    )
