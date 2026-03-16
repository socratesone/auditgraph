from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json

_TOKEN_SPLIT = re.compile(r"[\s_\-./]+")


def tokenize(text: str) -> list[str]:
    """Split text into searchable tokens on whitespace, underscores, hyphens, dots, slashes."""
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


def build_bm25_index(pkg_root: Path, entities: Iterable[dict[str, object]]) -> Path:
    inverted: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        name = str(entity.get("name", ""))
        entity_id = str(entity.get("id"))
        # Index the full name as a single key (for exact match)
        full_key = name.lower().strip()
        if full_key:
            inverted[full_key].append(entity_id)
        # Index individual tokens (for partial match)
        for token in tokenize(name):
            if token != full_key:
                inverted[token].append(entity_id)
        # Index aliases
        for alias in entity.get("aliases", []):
            alias_str = str(alias).lower().strip()
            if alias_str:
                inverted[alias_str].append(entity_id)
                for token in tokenize(alias_str):
                    if token != alias_str:
                        inverted[token].append(entity_id)

    index = {
        "type": "bm25",
        "entries": {k: sorted(set(v)) for k, v in inverted.items()},
    }
    index_path = pkg_root / "indexes" / "bm25" / "index.json"
    write_json(index_path, index)
    return index_path
