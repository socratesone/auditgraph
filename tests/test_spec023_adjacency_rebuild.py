"""Tests for Spec 023: Adjacency Index Rebuild."""
import json
import shutil
from pathlib import Path

import pytest

from auditgraph.index.adjacency_builder import build_adjacency_index

FIXTURES = Path(__file__).parent / "fixtures" / "spec023"


@pytest.fixture
def spec023_workspace(tmp_path):
    """Create a test workspace from spec023 fixtures."""
    shutil.copytree(FIXTURES / "entities", tmp_path / "entities")
    shutil.copytree(FIXTURES / "links", tmp_path / "links")
    return tmp_path


class TestBuildAdjacencyIndex:
    def test_builds_adjacency_from_all_links(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        adj = json.loads(adj_file.read_text())
        # There are 5 links with 4 distinct from_id values:
        #   ent_aa11bb22cc33 (modifies + authored_by)
        #   ent_bb22cc33dd44 (modifies + authored_by)
        #   ent_ff66aa11bb22 (CO_OCCURS_WITH)
        # So at least 3 distinct source entities in the adjacency map.
        assert len(adj) >= 3, (
            f"Expected at least 3 source entities in adjacency map, got {len(adj)}"
        )

    def test_includes_git_provenance_links(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        adj = json.loads(adj_file.read_text())
        # ent_aa11bb22cc33 has a "modifies" link and an "authored_by" link
        aa_edges = adj.get("ent_aa11bb22cc33", [])
        edge_types = {e["type"] for e in aa_edges}
        assert "modifies" in edge_types, (
            "modifies edge missing from adjacency for ent_aa11bb22cc33"
        )
        assert "authored_by" in edge_types, (
            "authored_by edge missing from adjacency for ent_aa11bb22cc33"
        )

    def test_includes_ner_links(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        adj = json.loads(adj_file.read_text())
        # ent_ff66aa11bb22 has a CO_OCCURS_WITH link
        ff_edges = adj.get("ent_ff66aa11bb22", [])
        edge_types = {e["type"] for e in ff_edges}
        assert "CO_OCCURS_WITH" in edge_types, (
            "CO_OCCURS_WITH edge missing from adjacency for ent_ff66aa11bb22"
        )

    def test_edge_structure(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        adj = json.loads(adj_file.read_text())
        required_keys = {"to_id", "type", "confidence", "rule_id"}
        for source_id, edges in adj.items():
            for edge in edges:
                missing = required_keys - set(edge.keys())
                assert not missing, (
                    f"Edge from {source_id} missing keys: {missing}"
                )

    def test_writes_to_correct_path(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        assert adj_file.exists(), (
            "Adjacency index not written to indexes/graph/adjacency.json"
        )

    def test_deterministic_output(self, spec023_workspace):
        build_adjacency_index(spec023_workspace)
        adj_file = spec023_workspace / "indexes" / "graph" / "adjacency.json"
        first_pass = adj_file.read_text()

        build_adjacency_index(spec023_workspace)
        second_pass = adj_file.read_text()

        assert first_pass == second_pass, "Adjacency index output is non-deterministic"
