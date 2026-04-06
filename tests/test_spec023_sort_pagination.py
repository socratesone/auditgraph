"""Tests for Spec 023 Phase 5: Sort and Pagination."""
import json
import shutil
from pathlib import Path

import pytest

from auditgraph.index.type_index import build_type_indexes

FIXTURES = Path(__file__).parent / "fixtures" / "spec023"


@pytest.fixture
def spec023_workspace(tmp_path):
    """Create a test workspace from spec023 fixtures with type indexes built."""
    entities_src = FIXTURES / "entities"
    links_src = FIXTURES / "links"
    shutil.copytree(entities_src, tmp_path / "entities")
    shutil.copytree(links_src, tmp_path / "links")
    entities = []
    for path in (tmp_path / "entities").rglob("*.json"):
        entities.append(json.loads(path.read_text()))
    build_type_indexes(tmp_path, entities)
    return tmp_path


# ---------------------------------------------------------------------------
# T038: apply_sort
# ---------------------------------------------------------------------------

class TestApplySort:
    def test_sort_ascending(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "b", "name": "beta"},
            {"id": "a", "name": "alpha"},
            {"id": "c", "name": "charlie"},
        ]
        result = apply_sort(entities, sort_field="name")
        assert [r["name"] for r in result] == ["alpha", "beta", "charlie"]

    def test_sort_descending(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "b", "name": "beta"},
            {"id": "a", "name": "alpha"},
            {"id": "c", "name": "charlie"},
        ]
        result = apply_sort(entities, sort_field="name", descending=True)
        assert [r["name"] for r in result] == ["charlie", "beta", "alpha"]

    def test_id_tiebreaker(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "c", "score": 10},
            {"id": "a", "score": 10},
            {"id": "b", "score": 10},
        ]
        result = apply_sort(entities, sort_field="score")
        assert [r["id"] for r in result] == ["a", "b", "c"]

    def test_missing_fields_last(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "b", "score": 5},
            {"id": "a"},
            {"id": "c", "score": 3},
        ]
        result = apply_sort(entities, sort_field="score")
        # Entities with values come first, missing field entity last
        assert result[0]["id"] == "c"
        assert result[1]["id"] == "b"
        assert result[2]["id"] == "a"

    def test_missing_fields_last_descending(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "b", "score": 5},
            {"id": "a"},
            {"id": "c", "score": 3},
        ]
        result = apply_sort(entities, sort_field="score", descending=True)
        assert result[0]["id"] == "b"
        assert result[1]["id"] == "c"
        assert result[2]["id"] == "a"  # missing still last

    def test_no_sort_field_returns_id_sorted(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "c"},
            {"id": "a"},
            {"id": "b"},
        ]
        result = apply_sort(entities, sort_field=None)
        assert [r["id"] for r in result] == ["a", "b", "c"]

    def test_numeric_sort(self):
        from auditgraph.query.filters import apply_sort

        entities = [
            {"id": "a", "count": 10},
            {"id": "b", "count": 2},
            {"id": "c", "count": 30},
        ]
        result = apply_sort(entities, sort_field="count")
        assert [r["count"] for r in result] == [2, 10, 30]


# ---------------------------------------------------------------------------
# T039: apply_pagination
# ---------------------------------------------------------------------------

class TestApplyPagination:
    def test_no_limit(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": str(i)} for i in range(5)]
        results, total = apply_pagination(entities)
        assert len(results) == 5
        assert total == 5

    def test_with_limit(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": str(i)} for i in range(5)]
        results, total = apply_pagination(entities, limit=2)
        assert len(results) == 2
        assert total == 5
        assert results[0]["id"] == "0"

    def test_with_offset(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": str(i)} for i in range(5)]
        results, total = apply_pagination(entities, limit=2, offset=2)
        assert len(results) == 2
        assert results[0]["id"] == "2"
        assert results[1]["id"] == "3"
        assert total == 5

    def test_offset_beyond_end(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": str(i)} for i in range(5)]
        results, total = apply_pagination(entities, offset=10)
        assert results == []
        assert total == 5

    def test_total_count_is_pre_pagination(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": str(i)} for i in range(10)]
        results, total = apply_pagination(entities, limit=3, offset=0)
        assert total == 10
        assert len(results) == 3


# ---------------------------------------------------------------------------
# T040: Integration with list_entities
# ---------------------------------------------------------------------------

class TestListEntitiesSortPagination:
    def test_sort_commits_by_authored_at_desc(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            sort="authored_at",
            descending=True,
        )
        dates = [r["authored_at"] for r in result["results"]]
        assert dates == sorted(dates, reverse=True)

    def test_limit_and_offset(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            sort="authored_at",
            limit=2,
            offset=0,
        )
        assert len(result["results"]) == 2
        assert result["total_count"] == 3
        assert result["truncated"] is True

    def test_truncated_false_when_all_fit(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            sort="authored_at",
            limit=10,
        )
        assert result["truncated"] is False

    def test_sort_ner_by_mention_count(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["ner:person"],
            sort="mention_count",
            descending=True,
            limit=2,
        )
        assert result["results"][0]["mention_count"] == 10
        assert result["results"][1]["mention_count"] == 5
        assert result["truncated"] is True

    def test_offset_past_results(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            offset=100,
        )
        assert result["results"] == []
        assert result["total_count"] == 3
