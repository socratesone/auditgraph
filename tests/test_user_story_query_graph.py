from __future__ import annotations

from pathlib import Path

from auditgraph.index.bm25 import build_bm25_index
from auditgraph.index.semantic import build_semantic_index
from auditgraph.query.keyword import keyword_search
from auditgraph.query.neighbors import neighbors
from auditgraph.query.node_view import node_view
from auditgraph.query.ranking import apply_ranking
from auditgraph.query.why_connected import why_connected
from auditgraph.extract.manifest import write_entities
from auditgraph.storage.artifacts import read_json, write_json
from tests.support import make_entity, pkg_root


def test_us2_keyword_search_returns_explanations(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    entity = make_entity("app.py", "repos/app.py")
    build_bm25_index(pkg, [entity])

    results = keyword_search(pkg, "app.py")

    assert results
    assert results[0]["id"] == entity["id"]
    assert "matched_terms" in results[0]["explanation"]


def test_us3_node_view_returns_refs(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    entity = make_entity("core.py", "repos/core.py")
    write_entities(pkg, [entity])

    payload = node_view(pkg, entity["id"])

    assert payload["id"] == entity["id"]
    assert payload["refs"]


def test_us4_neighbors_returns_edges(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    adjacency = {"ent_a": [{"to_id": "ent_b", "type": "related"}], "ent_b": []}
    write_json(pkg / "indexes" / "graph" / "adjacency.json", adjacency)

    payload = neighbors(pkg, "ent_a", depth=2)

    assert payload["center_id"] == "ent_a"
    assert payload["neighbors"] == adjacency["ent_a"]


def test_us12_semantic_ranking_is_deterministic(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    build_semantic_index(pkg, [{"id": "vec_a", "vector": [0.1, 0.2]}])

    ranked = apply_ranking(
        [
            {"id": "b", "score": 1.0, "explanation": {"tie_break": ["b"]}},
            {"id": "a", "score": 1.0, "explanation": {"tie_break": ["a"]}},
        ],
        rounding=0.1,
    )

    index = read_json(pkg / "indexes" / "vectors" / "index.json")
    assert index["vectors"]
    assert [item["id"] for item in ranked] == ["a", "b"]


def test_us13_why_connected_returns_rule(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    write_json(
        pkg / "indexes" / "graph" / "adjacency.json",
        {"ent_a": [{"to_id": "ent_b", "rule_id": "rule.v1"}]},
    )

    payload = why_connected(pkg, "ent_a", "ent_b")

    assert payload["path"]
    assert payload["path"][0]["rule_id"] == "rule.v1"
