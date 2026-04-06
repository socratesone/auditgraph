"""Tests for Spec 023 Phase 4: Filter engine (parse_predicate, matches, apply_filters)."""
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
# T027-T028: parse_predicate
# ---------------------------------------------------------------------------

class TestParsePredicate:
    def test_equality(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("author_email=alice@example.com")
        assert p.field == "author_email"
        assert p.operator == "="
        assert p.value == "alice@example.com"
        assert p.is_numeric is False

    def test_gte_numeric(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("confidence>=0.8")
        assert p.field == "confidence"
        assert p.operator == ">="
        assert p.value == "0.8"
        assert p.is_numeric is True

    def test_not_equal(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("name!=test")
        assert p.field == "name"
        assert p.operator == "!="
        assert p.value == "test"

    def test_contains(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("name~config")
        assert p.field == "name"
        assert p.operator == "~"
        assert p.value == "config"

    def test_lte(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("mention_count<=5")
        assert p.field == "mention_count"
        assert p.operator == "<="
        assert p.is_numeric is True

    def test_gt(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("mention_count>3")
        assert p.operator == ">"
        assert p.is_numeric is True

    def test_lt(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("mention_count<10")
        assert p.operator == "<"
        assert p.is_numeric is True

    def test_value_with_equals_sign(self):
        from auditgraph.query.filters import parse_predicate

        p = parse_predicate("name=foo=bar")
        assert p.field == "name"
        assert p.operator == "="
        assert p.value == "foo=bar"


# ---------------------------------------------------------------------------
# T029: matches
# ---------------------------------------------------------------------------

class TestMatches:
    def test_numeric_gte_true(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 5}, FilterPredicate("x", ">=", "5", True)) is True

    def test_numeric_gte_false(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 3}, FilterPredicate("x", ">=", "5", True)) is False

    def test_numeric_gt(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 6}, FilterPredicate("x", ">", "5", True)) is True
        assert matches({"x": 5}, FilterPredicate("x", ">", "5", True)) is False

    def test_numeric_lt(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 4}, FilterPredicate("x", "<", "5", True)) is True
        assert matches({"x": 5}, FilterPredicate("x", "<", "5", True)) is False

    def test_numeric_lte(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 5}, FilterPredicate("x", "<=", "5", True)) is True
        assert matches({"x": 6}, FilterPredicate("x", "<=", "5", True)) is False

    def test_numeric_eq(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 5}, FilterPredicate("x", "=", "5", True)) is True
        assert matches({"x": 4}, FilterPredicate("x", "=", "5", True)) is False

    def test_numeric_ne(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"x": 4}, FilterPredicate("x", "!=", "5", True)) is True
        assert matches({"x": 5}, FilterPredicate("x", "!=", "5", True)) is False

    def test_string_equality(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"name": "alice"}, FilterPredicate("name", "=", "alice", False)) is True
        assert matches({"name": "bob"}, FilterPredicate("name", "=", "alice", False)) is False

    def test_string_contains(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"name": "alice-config"}, FilterPredicate("name", "~", "config", False)) is True
        assert matches({"name": "alice"}, FilterPredicate("name", "~", "config", False)) is False

    def test_string_not_equal(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"name": "bob"}, FilterPredicate("name", "!=", "alice", False)) is True
        assert matches({"name": "alice"}, FilterPredicate("name", "!=", "alice", False)) is False

    def test_array_membership_eq(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "=", "a", False)) is True
        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "=", "c", False)) is False

    def test_array_substring_contains(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"aliases": ["Dr. Alice"]}, FilterPredicate("aliases", "~", "Alice", False)) is True
        assert matches({"aliases": ["Dr. Bob"]}, FilterPredicate("aliases", "~", "Alice", False)) is False

    def test_array_comparison_returns_false(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"aliases": ["a"]}, FilterPredicate("aliases", ">", "a", False)) is False

    def test_array_not_member(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "!=", "c", False)) is True
        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "!=", "a", False)) is False

    def test_missing_field_returns_false(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({}, FilterPredicate("x", "=", "5", False)) is False

    def test_bool_field(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"is_merge": True}, FilterPredicate("is_merge", "=", "true", False)) is True
        assert matches({"is_merge": False}, FilterPredicate("is_merge", "=", "true", False)) is False


# ---------------------------------------------------------------------------
# T030: apply_filters
# ---------------------------------------------------------------------------

class TestApplyFilters:
    def test_returns_iterator(self, spec023_workspace):
        import types
        from auditgraph.query.filters import apply_filters
        from auditgraph.storage.loaders import load_entities

        entities = load_entities(spec023_workspace)
        result = apply_filters(entities)
        assert isinstance(result, types.GeneratorType)

    def test_filter_by_type(self, spec023_workspace):
        from auditgraph.query.filters import apply_filters
        from auditgraph.storage.loaders import load_entities

        entities = load_entities(spec023_workspace)
        results = list(apply_filters(entities, types=["commit"]))
        assert len(results) == 3
        assert all(r["type"] == "commit" for r in results)

    def test_filter_by_predicate(self, spec023_workspace):
        from auditgraph.query.filters import apply_filters, parse_predicate
        from auditgraph.storage.loaders import load_entities

        entities = load_entities(spec023_workspace)
        pred = parse_predicate("author_email=alice@example.com")
        results = list(apply_filters(entities, predicates=[pred]))
        assert len(results) == 1
        assert results[0]["author_email"] == "alice@example.com"

    def test_filter_types_and_predicates(self, spec023_workspace):
        from auditgraph.query.filters import apply_filters, parse_predicate
        from auditgraph.storage.loaders import load_entities

        entities = load_entities(spec023_workspace)
        pred = parse_predicate("author_email=bob@example.com")
        results = list(apply_filters(entities, types=["commit"], predicates=[pred]))
        assert len(results) == 2
        assert all(r["author_email"] == "bob@example.com" for r in results)

    def test_list_entities_with_where(self, spec023_workspace):
        """Integration: list_entities with where predicates."""
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["commit"],
            where=["author_email=alice@example.com"],
        )
        assert result["total_count"] == 1
        assert result["results"][0]["author_email"] == "alice@example.com"

    def test_list_entities_numeric_where(self, spec023_workspace):
        """Integration: list_entities with numeric predicate."""
        from auditgraph.query.list_entities import list_entities

        result = list_entities(
            spec023_workspace,
            types=["ner:person"],
            where=["mention_count>=5"],
        )
        assert result["total_count"] == 2
        ids = {r["id"] for r in result["results"]}
        assert "ent_1122334455aa" in ids  # mention_count=5
        assert "ent_2233445566bb" in ids  # mention_count=10


# ---------------------------------------------------------------------------
# T077: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case tests for filter/pagination robustness."""

    def test_empty_workspace_yields_nothing(self):
        from auditgraph.query.filters import apply_filters

        results = list(apply_filters([], types=["commit"]))
        assert results == []

    def test_limit_zero_returns_empty(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        page, total = apply_pagination(entities, limit=0, offset=0)
        assert page == []
        assert total == 3

    def test_offset_beyond_count_returns_empty(self):
        from auditgraph.query.filters import apply_pagination

        entities = [{"id": "a"}, {"id": "b"}]
        page, total = apply_pagination(entities, limit=10, offset=999)
        assert page == []
        assert total == 2

    def test_type_filter_is_case_sensitive(self):
        from auditgraph.query.filters import apply_filters

        entities = [{"type": "commit", "id": "c1"}]
        results = list(apply_filters(entities, types=["Commit"]))
        assert results == []

    def test_where_field_name_is_case_sensitive(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"Name": "x"}, FilterPredicate("name", "=", "x", False)) is False

    def test_where_value_is_case_sensitive(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"name": "Config"}, FilterPredicate("name", "~", "config", False)) is False

    def test_array_field_with_comparison_operator(self):
        from auditgraph.query.filters import FilterPredicate, matches

        assert matches({"aliases": ["a"]}, FilterPredicate("aliases", ">=", "a", False)) is False

    def test_where_not_equal_on_array(self):
        from auditgraph.query.filters import FilterPredicate, matches

        # "c" is NOT a member of ["a", "b"] -> True
        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "!=", "c", False)) is True
        # "a" IS a member of ["a", "b"] -> False
        assert matches({"aliases": ["a", "b"]}, FilterPredicate("aliases", "!=", "a", False)) is False
