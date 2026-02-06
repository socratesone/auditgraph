from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable

from auditgraph.storage.hashing import sha256_text


def _link_id(rule_id: str, from_id: str, to_id: str) -> str:
    return f"lnk_{sha256_text(rule_id + ':' + from_id + ':' + to_id)}"


def build_source_cooccurrence_links(
    entities: Iterable[dict[str, object]],
    rule_id: str = "link.source_cooccurrence.v1",
) -> list[dict[str, object]]:
    by_source: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for entity in entities:
        entity_id = str(entity.get("id", ""))
        refs = entity.get("refs", [])
        if not entity_id or not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            source_path = str(ref.get("source_path", ""))
            source_hash = str(ref.get("source_hash", ""))
            if source_path:
                by_source[source_path].append((entity_id, source_hash))

    links: list[dict[str, object]] = []
    for source_path, entries in by_source.items():
        entries_sorted = sorted(entries, key=lambda item: item[0])
        ids = [entry[0] for entry in entries_sorted]
        source_hash = entries_sorted[0][1] if entries_sorted else ""
        for from_id, to_id in combinations(ids, 2):
            for a, b in ((from_id, to_id), (to_id, from_id)):
                links.append(
                    {
                        "id": _link_id(rule_id, a, b),
                        "from_id": a,
                        "to_id": b,
                        "type": "relates_to",
                        "rule_id": rule_id,
                        "confidence": 1.0,
                        "authority": "authoritative",
                        "evidence": [
                            {
                                "source_path": source_path,
                                "source_hash": source_hash,
                            }
                        ],
                    }
                )
    return links
