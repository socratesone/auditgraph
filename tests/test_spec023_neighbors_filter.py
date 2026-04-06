"""Tests for Spec 023 Phase 6: Neighbors edge-type and confidence filtering."""
import json
import shutil
from pathlib import Path

import pytest

from auditgraph.index.adjacency_builder import build_adjacency_index

FIXTURES = Path(__file__).parent / "fixtures" / "spec023"


@pytest.fixture
def spec023_workspace(tmp_path):
    """Create a test workspace with adjacency index built."""
    entities_src = FIXTURES / "entities"
    links_src = FIXTURES / "links"
    shutil.copytree(entities_src, tmp_path / "entities")
    shutil.copytree(links_src, tmp_path / "links")
    build_adjacency_index(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# T047-T048: neighbors with edge_types and min_confidence
# ---------------------------------------------------------------------------

class TestNeighborsEdgeTypeFilter:
    def test_no_filter_returns_all_edges(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        # ent_aa11bb22cc33 has: modifies (to dd44), authored_by (to ff66)
        result = neighbors(spec023_workspace, "ent_aa11bb22cc33")
        assert len(result["neighbors"]) == 2

    def test_filter_by_edge_type_authored_by(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(spec023_workspace, "ent_aa11bb22cc33", edge_types=["authored_by"])
        assert len(result["neighbors"]) == 1
        assert result["neighbors"][0]["type"] == "authored_by"

    def test_filter_by_edge_type_modifies(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(spec023_workspace, "ent_aa11bb22cc33", edge_types=["modifies"])
        assert len(result["neighbors"]) == 1
        assert result["neighbors"][0]["type"] == "modifies"

    def test_filter_multiple_edge_types(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(
            spec023_workspace,
            "ent_aa11bb22cc33",
            edge_types=["modifies", "authored_by"],
        )
        assert len(result["neighbors"]) == 2

    def test_filter_nonexistent_edge_type(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(spec023_workspace, "ent_aa11bb22cc33", edge_types=["nonexistent"])
        assert result["neighbors"] == []

    def test_min_confidence_filters_low(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        # ent_ff66aa11bb22 has CO_OCCURS_WITH (confidence 0.6) to ent_1122334455aa
        result = neighbors(spec023_workspace, "ent_ff66aa11bb22", min_confidence=0.8)
        # Only edges with confidence >= 0.8 should remain
        co_occurs = [e for e in result["neighbors"] if e["type"] == "CO_OCCURS_WITH"]
        assert len(co_occurs) == 0

    def test_min_confidence_keeps_high(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(spec023_workspace, "ent_ff66aa11bb22", min_confidence=0.5)
        co_occurs = [e for e in result["neighbors"] if e["type"] == "CO_OCCURS_WITH"]
        assert len(co_occurs) == 1

    def test_combined_edge_type_and_confidence(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        result = neighbors(
            spec023_workspace,
            "ent_ff66aa11bb22",
            edge_types=["CO_OCCURS_WITH"],
            min_confidence=0.8,
        )
        assert result["neighbors"] == []

    def test_depth_with_edge_filter(self, spec023_workspace):
        from auditgraph.query.neighbors import neighbors

        # depth=2 with type filter should only traverse matching edges
        result = neighbors(
            spec023_workspace,
            "ent_aa11bb22cc33",
            depth=2,
            edge_types=["authored_by"],
        )
        # Only authored_by edges should appear
        assert all(e["type"] == "authored_by" for e in result["neighbors"])
