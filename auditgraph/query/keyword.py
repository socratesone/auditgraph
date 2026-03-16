from __future__ import annotations

from collections import Counter
from pathlib import Path

from auditgraph.index.bm25 import tokenize
from auditgraph.query.ranking import apply_ranking
from auditgraph.storage.artifacts import read_json
from auditgraph.storage.loaders import load_chunks


def keyword_search(
    pkg_root: Path,
    query: str,
    enable_semantic: bool = False,
    score_rounding: float = 0.000001,
) -> list[dict[str, object]]:
    index_path = pkg_root / "indexes" / "bm25" / "index.json"
    results = []
    if index_path.exists():
        index = read_json(index_path)
        entries = index.get("entries", {})

        # Try exact match first
        query_lower = query.lower().strip()
        exact_hits = entries.get(query_lower, [])

        # Tokenize the query and collect hits per entity with match counts
        query_tokens = tokenize(query)
        entity_matches: Counter[str] = Counter()
        matched_terms_map: dict[str, list[str]] = {}

        # Exact match gets highest weight
        for eid in exact_hits:
            entity_matches[eid] += len(query_tokens) + 1
            matched_terms_map.setdefault(eid, []).append(query_lower)

        # Token matches
        for token in query_tokens:
            token_hits = entries.get(token, [])
            for eid in token_hits:
                entity_matches[eid] += 1
                matched_terms_map.setdefault(eid, []).append(token)

        # Build results scored by fraction of query tokens matched
        total_tokens = max(len(query_tokens), 1)
        for entity_id, match_count in entity_matches.items():
            score = min(match_count / total_tokens, 1.0)
            terms = sorted(set(matched_terms_map.get(entity_id, [])))
            results.append(
                {
                    "id": entity_id,
                    "score": score,
                    "explanation": {
                        "matched_terms": terms,
                        "bm25_score": score,
                        "semantic_score": 0.0,
                        "graph_boost": 0.0,
                        "tie_break": [entity_id],
                    },
                }
            )
    ranked = apply_ranking(results, score_rounding)
    chunk_results: list[dict[str, object]] = []
    query_token = query.strip().lower()
    if query_token:
        chunks = load_chunks(pkg_root)
        for chunk in chunks:
            text = str(chunk.get("text", ""))
            if query_token not in text.lower():
                continue
            chunk_results.append(
                {
                    "id": str(chunk.get("chunk_id", "")),
                    "score": 1.0,
                    "text": text,
                    "citation": {
                        "source_path": chunk.get("source_path"),
                        "source_hash": chunk.get("source_hash"),
                        "page_start": chunk.get("page_start"),
                        "page_end": chunk.get("page_end"),
                        "paragraph_index_start": chunk.get("paragraph_index_start"),
                        "paragraph_index_end": chunk.get("paragraph_index_end"),
                    },
                    "explanation": {
                        "matched_terms": [query],
                        "bm25_score": 1.0,
                        "semantic_score": 0.0,
                        "graph_boost": 0.0,
                        "tie_break": [str(chunk.get("document_id", "")), int(chunk.get("order", 0))],
                    },
                }
            )
    ranked_chunks = apply_ranking(chunk_results, score_rounding)
    if enable_semantic:
        return ranked + ranked_chunks
    return ranked + ranked_chunks
