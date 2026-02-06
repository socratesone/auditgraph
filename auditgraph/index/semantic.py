from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json


def build_semantic_index(pkg_root: Path, vectors: Iterable[dict[str, object]]) -> Path:
    index_path = pkg_root / "indexes" / "vectors" / "index.json"
    write_json(index_path, {"vectors": list(vectors)})
    return index_path
