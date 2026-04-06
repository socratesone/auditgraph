"""Tests for Spec 023 Phase 3: list_entities command with type filtering."""
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
    # Build type indexes so load_entities_by_type works
    entities = []
    for path in (tmp_path / "entities").rglob("*.json"):
        entities.append(json.loads(path.read_text()))
    build_type_indexes(tmp_path, entities)
    return tmp_path


class TestListEntitiesTypeFilter:
    """T020-T021: list_entities with type filtering."""

    def test_filter_single_type_commit(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["commit"])
        assert all(r["type"] == "commit" for r in result["results"])
        assert result["total_count"] == 3

    def test_filter_single_type_file(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["file"])
        assert all(r["type"] == "file" for r in result["results"])
        assert result["total_count"] == 2

    def test_filter_multiple_types_or(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["commit", "file"])
        types_found = {r["type"] for r in result["results"]}
        assert "commit" in types_found
        assert "file" in types_found
        assert result["total_count"] == 5

    def test_filter_nonexistent_type(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["nonexistent"])
        assert result["results"] == []
        assert result["total_count"] == 0

    def test_no_type_filter_returns_all(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace)
        assert result["total_count"] == 8

    def test_response_envelope_keys(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["commit"])
        assert "results" in result
        assert "total_count" in result
        assert "truncated" in result
        assert "limit" in result
        assert "offset" in result

    def test_truncated_false_when_no_limit(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace)
        assert result["truncated"] is False

    def test_ner_person_type_with_colon(self, spec023_workspace):
        from auditgraph.query.list_entities import list_entities

        result = list_entities(spec023_workspace, types=["ner:person"])
        assert result["total_count"] == 3
        assert all(r["type"] == "ner:person" for r in result["results"])
