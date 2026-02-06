from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json


def load_adjacency(pkg_root: Path) -> dict[str, list[dict[str, object]]]:
    path = pkg_root / "indexes" / "graph" / "adjacency.json"
    if not path.exists():
        return {}
    data = read_json(path)
    return {str(k): v for k, v in data.items()}
