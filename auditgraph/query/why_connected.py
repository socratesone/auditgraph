from __future__ import annotations

from pathlib import Path

from auditgraph.link.adjacency import load_adjacency


def why_connected(pkg_root: Path, from_id: str, to_id: str) -> dict[str, object]:
    adjacency = load_adjacency(pkg_root)
    for edge in adjacency.get(from_id, []):
        if edge.get("to_id") == to_id:
            return {"path": [edge]}
    return {"path": []}
