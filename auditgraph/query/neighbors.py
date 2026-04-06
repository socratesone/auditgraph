from __future__ import annotations

from pathlib import Path

from auditgraph.link.adjacency import load_adjacency


def neighbors(
    pkg_root: Path,
    entity_id: str,
    depth: int = 1,
    edge_types: list[str] | None = None,
    min_confidence: float | None = None,
) -> dict[str, object]:
    adjacency = load_adjacency(pkg_root)
    edge_type_set = set(edge_types) if edge_types else None
    seen = {entity_id}
    frontier = [entity_id]
    edges: list[dict[str, object]] = []

    for _ in range(depth):
        next_frontier: list[str] = []
        for node_id in frontier:
            for edge in adjacency.get(node_id, []):
                # Apply edge-type filter
                if edge_type_set and edge.get("type") not in edge_type_set:
                    continue
                # Apply min-confidence filter
                if min_confidence is not None:
                    conf = edge.get("confidence", 1.0)
                    if isinstance(conf, (int, float)) and conf < min_confidence:
                        continue
                edges.append(edge)
                target = edge.get("to_id")
                if isinstance(target, str) and target not in seen:
                    seen.add(target)
                    next_frontier.append(target)
        frontier = next_frontier

    return {"center_id": entity_id, "neighbors": edges}
