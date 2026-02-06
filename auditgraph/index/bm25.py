from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json


def build_bm25_index(pkg_root: Path, entities: Iterable[dict[str, object]]) -> Path:
    inverted: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        name = str(entity.get("name", ""))
        entity_id = str(entity.get("id"))
        for token in name.lower().split():
            inverted[token].append(entity_id)

    index = {
        "type": "bm25",
        "entries": {k: sorted(set(v)) for k, v in inverted.items()},
    }
    index_path = pkg_root / "indexes" / "bm25" / "index.json"
    write_json(index_path, index)
    return index_path
