from __future__ import annotations

from pathlib import Path

from auditgraph.query.ranking import apply_ranking
from auditgraph.storage.artifacts import read_json


def keyword_search(
    pkg_root: Path,
    query: str,
    enable_semantic: bool = False,
    score_rounding: float = 0.000001,
) -> list[dict[str, object]]:
    index_path = pkg_root / "indexes" / "bm25" / "index.json"
    if not index_path.exists():
        return []

    index = read_json(index_path)
    entries = index.get("entries", {})
    hits = entries.get(query.lower(), [])
    results = []
    for entity_id in hits:
        results.append(
            {
                "id": entity_id,
                "score": 1.0,
                "explanation": {
                    "matched_terms": [query],
                    "bm25_score": 1.0,
                    "semantic_score": 0.0,
                    "graph_boost": 0.0,
                    "tie_break": [entity_id],
                },
            }
        )
    ranked = apply_ranking(results, score_rounding)
    if enable_semantic:
        return ranked
    return ranked
