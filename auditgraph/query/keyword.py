from __future__ import annotations

from pathlib import Path

from auditgraph.query.filters import (
    apply_filters,
    apply_sort,
    parse_predicate,
)
from auditgraph.query.ranking import apply_ranking
from auditgraph.storage.artifacts import read_json
from auditgraph.storage.loaders import load_chunks, load_entity


def keyword_search(
    pkg_root: Path,
    query: str,
    enable_semantic: bool = False,
    score_rounding: float = 0.000001,
    *,
    types: list[str] | None = None,
    where: list[str] | None = None,
    sort: str | None = None,
    descending: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    index_path = pkg_root / "indexes" / "bm25" / "index.json"
    results = []
    if index_path.exists():
        index = read_json(index_path)
        entries = index.get("entries", {})
        hits = entries.get(query.lower(), [])
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

    # Apply filter engine to BM25 results
    need_filter = types or where or sort or limit is not None or offset > 0
    if need_filter and ranked:
        # Load full entity data for each hit so filters can inspect fields
        predicates = [parse_predicate(w) for w in where] if where else None
        enriched: list[dict[str, object]] = []
        for hit in ranked:
            entity_id = str(hit["id"])
            try:
                entity = load_entity(pkg_root, entity_id)
            except Exception:
                continue
            enriched.append({"_hit": hit, "_entity": entity})

        # Filter by types and predicates on the entity data
        entity_list = [item["_entity"] for item in enriched]
        hit_map = {str(item["_entity"]["id"]): item["_hit"] for item in enriched}

        filtered = list(apply_filters(entity_list, types=types, predicates=predicates))

        # Sort if requested
        if sort:
            filtered = apply_sort(filtered, sort_field=sort, descending=descending)

        # Pagination
        total = len(filtered)
        page = filtered[offset:]
        if limit is not None:
            page = page[:limit]

        # Rebuild ranked results preserving original hit structure
        ranked = []
        for entity in page:
            eid = str(entity["id"])
            if eid in hit_map:
                ranked.append(hit_map[eid])

    chunk_results: list[dict[str, object]] = []
    query_token = query.strip().lower()
    if query_token and not need_filter:
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
    return ranked
