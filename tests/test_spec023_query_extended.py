"""Tests for Spec 023 Phase 8: Extended keyword_search with filter params."""
import json
import shutil
from pathlib import Path

import pytest

from auditgraph.index.type_index import build_type_indexes

FIXTURES = Path(__file__).parent / "fixtures" / "spec023"


@pytest.fixture
def spec023_workspace(tmp_path):
    """Create a test workspace with BM25 index and type indexes."""
    entities_src = FIXTURES / "entities"
    links_src = FIXTURES / "links"
    shutil.copytree(entities_src, tmp_path / "entities")
    shutil.copytree(links_src, tmp_path / "links")
    # Build type indexes
    entities = []
    for path in (tmp_path / "entities").rglob("*.json"):
        entities.append(json.loads(path.read_text()))
    build_type_indexes(tmp_path, entities)
    # Build a minimal BM25 index with some entity IDs keyed by terms
    bm25_dir = tmp_path / "indexes" / "bm25"
    bm25_dir.mkdir(parents=True, exist_ok=True)
    bm25_index = {
        "entries": {
            "auth": [
                "ent_aa11bb22cc33",  # commit by alice
                "ent_bb22cc33dd44",  # commit by bob
                "ent_dd44ee55ff66",  # file: login.py
                "ent_ee55ff66aa11",  # file: session.py
            ],
            "login": [
                "ent_aa11bb22cc33",  # commit
                "ent_dd44ee55ff66",  # file: login.py
            ],
        }
    }
    (bm25_dir / "index.json").write_text(json.dumps(bm25_index))
    return tmp_path


# ---------------------------------------------------------------------------
# T061: backwards compatibility
# ---------------------------------------------------------------------------

class TestKeywordSearchBackwardsCompat:
    def test_basic_search_still_works(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(spec023_workspace, "auth")
        assert len(results) == 4
        ids = {r["id"] for r in results}
        assert "ent_aa11bb22cc33" in ids

    def test_empty_query(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(spec023_workspace, "")
        assert results == []

    def test_no_match(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(spec023_workspace, "zzzznotfound")
        assert results == []


# ---------------------------------------------------------------------------
# T061: keyword_search with types filter
# ---------------------------------------------------------------------------

class TestKeywordSearchWithFilters:
    def test_with_types_filter(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(spec023_workspace, "auth", types=["commit"])
        ids = {r["id"] for r in results}
        assert "ent_aa11bb22cc33" in ids
        assert "ent_bb22cc33dd44" in ids
        # File entities should be filtered out
        assert "ent_dd44ee55ff66" not in ids
        assert "ent_ee55ff66aa11" not in ids

    def test_with_where_filter(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(
            spec023_workspace,
            "auth",
            types=["commit"],
            where=["author_email=alice@example.com"],
        )
        assert len(results) == 1
        assert results[0]["id"] == "ent_aa11bb22cc33"

    def test_with_sort(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(
            spec023_workspace,
            "auth",
            types=["commit"],
            sort="authored_at",
            descending=True,
        )
        assert len(results) == 2
        # Should be sorted by authored_at descending
        dates = [r.get("_entity", {}).get("authored_at") or "" for r in results]
        # The results carry entity info for filtering; check IDs are in correct order
        ids = [r["id"] for r in results]
        assert ids[0] == "ent_bb22cc33dd44"  # 2025-05-16
        assert ids[1] == "ent_aa11bb22cc33"  # 2025-05-15

    def test_with_limit(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(
            spec023_workspace,
            "auth",
            limit=2,
        )
        assert len(results) == 2

    def test_types_and_limit_combined(self, spec023_workspace):
        from auditgraph.query.keyword import keyword_search

        results = keyword_search(
            spec023_workspace,
            "login",
            types=["file"],
            limit=1,
        )
        assert len(results) == 1
        assert results[0]["id"] == "ent_dd44ee55ff66"
