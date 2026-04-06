"""Forward adjacency index builder from all link files."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def build_adjacency_index(pkg_root: Path) -> Path:
    """Rebuild indexes/graph/adjacency.json from all link files.

    Reads all links from pkg_root/links/.
    Builds: {from_id: [{to_id, type, confidence, rule_id}, ...]}.
    Writes atomically. Returns path.
    """
    links_dir = pkg_root / "links"
    adjacency: dict[str, list[dict[str, object]]] = defaultdict(list)

    if links_dir.exists():
        for path in sorted(links_dir.rglob("*.json"), key=lambda p: p.name):
            data = json.loads(path.read_text())
            from_id = str(data.get("from_id", ""))
            if not from_id:
                continue
            edge = {
                "to_id": str(data.get("to_id", "")),
                "type": str(data.get("type", "")),
                "confidence": data.get("confidence", 1.0),
                "rule_id": str(data.get("rule_id", "")),
            }
            adjacency[from_id].append(edge)

    # Sort edges within each source for determinism
    for from_id in adjacency:
        adjacency[from_id].sort(key=lambda e: (e["type"], e["to_id"]))

    # Sort by source ID for deterministic output
    sorted_adj = dict(sorted(adjacency.items()))

    out_dir = pkg_root / "indexes" / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "adjacency.json"
    out_path.write_text(json.dumps(sorted_adj, indent=2))

    return out_path
