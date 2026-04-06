"""Tests for Spec 023: Type Index and Storage Loaders."""
import json
import shutil
import types
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "spec023"


@pytest.fixture
def spec023_workspace(tmp_path):
    """Create a test workspace from spec023 fixtures."""
    entities_src = FIXTURES / "entities"
    links_src = FIXTURES / "links"
    entities_dst = tmp_path / "entities"
    links_dst = tmp_path / "links"
    shutil.copytree(entities_src, entities_dst)
    shutil.copytree(links_src, links_dst)
    return tmp_path


# ---------------------------------------------------------------------------
# T004 -- sanitize_type_name
# ---------------------------------------------------------------------------

from auditgraph.index.type_index import sanitize_type_name


class TestSanitizeTypeName:
    def test_colon_replaced(self):
        assert sanitize_type_name("ner:person") == "ner_person"

    def test_colon_and_prefix(self):
        assert sanitize_type_name("ag:file") == "ag_file"

    def test_no_special_chars(self):
        assert sanitize_type_name("commit") == "commit"

    def test_multiple_colons(self):
        assert sanitize_type_name("a:b:c") == "a_b_c"

    def test_empty_string(self):
        assert sanitize_type_name("") == ""


# ---------------------------------------------------------------------------
# T005 -- build_type_indexes
# ---------------------------------------------------------------------------

from auditgraph.index.type_index import build_type_indexes


class TestBuildTypeIndexes:
    def _load_entities(self, workspace):
        """Load all entity fixtures from the workspace."""
        entities = []
        for path in (workspace / "entities").rglob("*.json"):
            with open(path) as f:
                entities.append(json.load(f))
        return entities

    def test_commit_index_exists(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "commit.json"
        assert index_file.exists(), "commit.json type index was not created"

    def test_commit_index_contains_three_ids(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "commit.json"
        ids = json.loads(index_file.read_text())
        assert isinstance(ids, list)
        assert len(ids) == 3

    def test_ner_person_index_exists(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "ner_person.json"
        assert index_file.exists(), "ner_person.json type index was not created"

    def test_ner_person_index_contains_three_ids(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "ner_person.json"
        ids = json.loads(index_file.read_text())
        assert isinstance(ids, list)
        assert len(ids) == 3

    def test_file_index_exists(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "file.json"
        assert index_file.exists(), "file.json type index was not created"

    def test_file_index_contains_two_ids(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        index_file = spec023_workspace / "indexes" / "types" / "file.json"
        ids = json.loads(index_file.read_text())
        assert isinstance(ids, list)
        assert len(ids) == 2

    def test_index_values_are_strings(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        for name in ("commit.json", "ner_person.json", "file.json"):
            index_file = spec023_workspace / "indexes" / "types" / name
            ids = json.loads(index_file.read_text())
            assert all(isinstance(i, str) for i in ids), f"Non-string ID in {name}"

    def test_deterministic_output(self, spec023_workspace):
        entities = self._load_entities(spec023_workspace)
        build_type_indexes(spec023_workspace, entities)
        first_pass = {}
        for name in ("commit.json", "ner_person.json", "file.json"):
            index_file = spec023_workspace / "indexes" / "types" / name
            first_pass[name] = index_file.read_text()

        # Second call
        build_type_indexes(spec023_workspace, entities)
        for name in ("commit.json", "ner_person.json", "file.json"):
            index_file = spec023_workspace / "indexes" / "types" / name
            assert index_file.read_text() == first_pass[name], (
                f"Non-deterministic output for {name}"
            )


# ---------------------------------------------------------------------------
# T006 -- build_link_type_indexes
# ---------------------------------------------------------------------------

from auditgraph.index.type_index import build_link_type_indexes


class TestBuildLinkTypeIndexes:
    def test_modifies_index_exists(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "modifies.json"
        assert index_file.exists(), "modifies.json link-type index was not created"

    def test_modifies_index_contains_two_ids(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "modifies.json"
        ids = json.loads(index_file.read_text())
        assert len(ids) == 2

    def test_authored_by_index_exists(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "authored_by.json"
        assert index_file.exists(), "authored_by.json link-type index was not created"

    def test_authored_by_index_contains_two_ids(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "authored_by.json"
        ids = json.loads(index_file.read_text())
        assert len(ids) == 2

    def test_co_occurs_with_index_exists(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "CO_OCCURS_WITH.json"
        assert index_file.exists(), "CO_OCCURS_WITH.json link-type index was not created"

    def test_co_occurs_with_index_contains_one_id(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        index_file = spec023_workspace / "indexes" / "link-types" / "CO_OCCURS_WITH.json"
        ids = json.loads(index_file.read_text())
        assert len(ids) == 1

    def test_link_index_values_are_strings(self, spec023_workspace):
        build_link_type_indexes(spec023_workspace)
        link_types_dir = spec023_workspace / "indexes" / "link-types"
        for index_file in link_types_dir.glob("*.json"):
            ids = json.loads(index_file.read_text())
            assert all(isinstance(i, str) for i in ids), (
                f"Non-string ID in {index_file.name}"
            )


# ---------------------------------------------------------------------------
# T007 -- load_entities_by_type
# ---------------------------------------------------------------------------

from auditgraph.storage.loaders import load_entities_by_type


class TestLoadEntitiesByType:
    def _setup_indexes(self, workspace):
        """Build type indexes so load_entities_by_type can use them."""
        entities = []
        for path in (workspace / "entities").rglob("*.json"):
            with open(path) as f:
                entities.append(json.load(f))
        build_type_indexes(workspace, entities)
        return entities

    def test_returns_generator(self, spec023_workspace):
        self._setup_indexes(spec023_workspace)
        result = load_entities_by_type(spec023_workspace, "commit")
        assert isinstance(result, types.GeneratorType), (
            "load_entities_by_type should return a generator"
        )

    def test_commit_yields_three(self, spec023_workspace):
        self._setup_indexes(spec023_workspace)
        results = list(load_entities_by_type(spec023_workspace, "commit"))
        assert len(results) == 3

    def test_commit_entities_have_correct_type(self, spec023_workspace):
        self._setup_indexes(spec023_workspace)
        for entity in load_entities_by_type(spec023_workspace, "commit"):
            assert entity["type"] == "commit"

    def test_file_yields_two(self, spec023_workspace):
        self._setup_indexes(spec023_workspace)
        results = list(load_entities_by_type(spec023_workspace, "file"))
        assert len(results) == 2

    def test_nonexistent_type_yields_nothing(self, spec023_workspace):
        self._setup_indexes(spec023_workspace)
        results = list(load_entities_by_type(spec023_workspace, "nonexistent"))
        assert len(results) == 0


# ---------------------------------------------------------------------------
# T008 -- load_links / load_links_by_type
# ---------------------------------------------------------------------------

from auditgraph.storage.loaders import load_links, load_links_by_type


class TestLoadLinks:
    def test_returns_generator(self, spec023_workspace):
        result = load_links(spec023_workspace)
        assert isinstance(result, types.GeneratorType), (
            "load_links should return a generator"
        )

    def test_yields_all_five_links(self, spec023_workspace):
        results = list(load_links(spec023_workspace))
        assert len(results) == 5


class TestLoadLinksByType:
    def _setup_link_indexes(self, workspace):
        build_link_type_indexes(workspace)

    def test_returns_generator(self, spec023_workspace):
        self._setup_link_indexes(spec023_workspace)
        result = load_links_by_type(spec023_workspace, "modifies")
        assert isinstance(result, types.GeneratorType), (
            "load_links_by_type should return a generator"
        )

    def test_modifies_yields_two(self, spec023_workspace):
        self._setup_link_indexes(spec023_workspace)
        results = list(load_links_by_type(spec023_workspace, "modifies"))
        assert len(results) == 2

    def test_nonexistent_type_yields_nothing(self, spec023_workspace):
        self._setup_link_indexes(spec023_workspace)
        results = list(load_links_by_type(spec023_workspace, "nonexistent"))
        assert len(results) == 0
