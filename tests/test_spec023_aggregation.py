"""Tests for Spec 023 Phase 7: Aggregation (count-only and group-by)."""
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
# T054: apply_aggregation
# ---------------------------------------------------------------------------

class TestApplyAggregation:
    def test_count_only(self):
        from auditgraph.query.filters import apply_aggregation

        entities = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        result = apply_aggregation(entities, count_only=True)
        assert result == {"count": 3}

    def test_group_by_field(self):
        from auditgraph.query.filters import apply_aggregation

        entities = [
            {"id": "a", "type": "commit"},
            {"id": "b", "type": "commit"},
            {"id": "c", "type": "file"},
        ]
        result = apply_aggregation(entities, group_by="type")
        assert result["groups"]["commit"] == 2
        assert result["groups"]["file"] == 1
        assert result["total_count"] == 3

    def test_group_by_missing_field(self):
        from auditgraph.query.filters import apply_aggregation

        entities = [
            {"id": "a", "type": "commit"},
            {"id": "b"},
        ]
        result = apply_aggregation(entities, group_by="type")
        assert result["groups"]["commit"] == 1
        assert result["groups"]["_missing"] == 1

    def test_no_aggregation_returns_none(self):
        from auditgraph.query.filters import apply_aggregation

        entities = [{"id": "a"}]
        result = apply_aggregation(entities)
        assert result is None

    def test_count_only_and_group_by(self):
        """When both count_only and group_by, group_by takes precedence."""
        from auditgraph.query.filters import apply_aggregation

        entities = [
            {"id": "a", "type": "commit"},
            {"id": "b", "type": "file"},
        ]
        result = apply_aggregation(entities, count_only=True, group_by="type")
        assert "groups" in result
        assert result["total_count"] == 2


# ---------------------------------------------------------------------------
# T055: Integration with list_entities
# ---------------------------------------------------------------------------

class TestListEntitiesAggregation:
    def test_count_only(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["commit"], count_only=True)
        assert result["count"] == 3
        assert "results" not in result

    def test_group_by_type(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, group_by="type")
        assert result["groups"]["commit"] == 3
        assert result["groups"]["file"] == 2
        assert result["groups"]["ner:person"] == 3
        assert result["total_count"] == 8

    def test_group_by_with_type_filter(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            group_by="author_email",
        )
        assert result["groups"]["alice@example.com"] == 1
        assert result["groups"]["bob@example.com"] == 2
        assert result["total_count"] == 3

    def test_group_by_with_where(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            where=["is_merge=false"],
            group_by="author_email",
        )
        assert result["groups"]["alice@example.com"] == 1
        assert result["groups"]["bob@example.com"] == 1
        assert result["total_count"] == 2
