from __future__ import annotations

from pathlib import Path

from auditgraph.link.adjacency import load_adjacency


def neighbors(pkg_root: Path, entity_id: str, depth: int = 1) -> dict[str, object]:
    adjacency = load_adjacency(pkg_root)
    seen = {entity_id}
    frontier = [entity_id]
    edges: list[dict[str, object]] = []

    for _ in range(depth):
        next_frontier: list[str] = []
        for node_id in frontier:
            for edge in adjacency.get(node_id, []):
                edges.append(edge)
                target = edge.get("to_id")
                if isinstance(target, str) and target not in seen:
                    seen.add(target)
                    next_frontier.append(target)
        frontier = next_frontier

    return {"center_id": entity_id, "neighbors": edges}
