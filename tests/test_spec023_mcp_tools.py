"""Spec 023 Phase 9 – MCP Integration tests.

Verifies tool manifest entries for ag_list, extended ag_query, extended
ag_neighbors, mcp_inventory, and build_command adapter.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "llm-tooling" / "tool.manifest.json"
ADAPTER_MODULE_PATH = PROJECT_ROOT / "llm-tooling" / "mcp" / "adapters" / "project.py"


def _load_adapter_module():
    """Load llm-tooling/mcp/adapters/project.py without it being a package."""
    spec = importlib.util.spec_from_file_location("project_adapter", ADAPTER_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {ADAPTER_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def _tool_by_name(manifest: dict, name: str) -> dict:
    for tool in manifest["tools"]:
        if tool["name"] == name:
            return tool
    raise KeyError(f"Tool {name!r} not found in manifest")


# ── T067: ag_list tool entry ──────────────────────────────────────────


class TestAgListManifest:
    def test_ag_list_exists(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_list")
        assert tool["command"] == "list"

    def test_ag_list_title(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_list")
        assert tool["title"] == "List Entities"

    def test_ag_list_risk_is_low(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_list")
        assert tool["risk"] == "low"

    def test_ag_list_is_idempotent(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_list")
        assert tool["idempotency"] == "idempotent"

    def test_ag_list_read_only(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_list")
        assert tool["constraints"]["read_only_safe"] is True

    def test_ag_list_schema_has_type(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "type" in props
        assert props["type"]["type"] == "string"

    def test_ag_list_schema_has_where(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "where" in props

    def test_ag_list_schema_has_sort(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "sort" in props

    def test_ag_list_schema_has_limit(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "limit" in props
        assert props["limit"]["type"] == "integer"
        assert props["limit"]["default"] == 100

    def test_ag_list_schema_has_offset(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "offset" in props
        assert props["offset"]["type"] == "integer"

    def test_ag_list_schema_has_count(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "count" in props
        assert props["count"]["type"] == "boolean"

    def test_ag_list_schema_has_group_by(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_list")["input_schema"]["properties"]
        assert "group_by" in props

    def test_ag_list_no_additional_properties(self, manifest: dict) -> None:
        schema = _tool_by_name(manifest, "ag_list")["input_schema"]
        assert schema["additionalProperties"] is False


# ── T068: ag_query extended schema ────────────────────────────────────


class TestAgQueryExtendedSchema:
    def test_ag_query_has_type(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "type" in props

    def test_ag_query_has_where(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "where" in props

    def test_ag_query_has_sort(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "sort" in props

    def test_ag_query_has_limit(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "limit" in props

    def test_ag_query_has_offset(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "offset" in props

    def test_ag_query_still_has_q(self, manifest: dict) -> None:
        """Backwards compat: 'q' param must remain."""
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "q" in props

    def test_ag_query_still_has_root(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "root" in props

    def test_ag_query_still_has_config(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_query")["input_schema"]["properties"]
        assert "config" in props


# ── T068: ag_neighbors extended schema ────────────────────────────────


class TestAgNeighborsExtendedSchema:
    def test_ag_neighbors_has_edge_type(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_neighbors")["input_schema"]["properties"]
        assert "edge_type" in props
        assert props["edge_type"]["type"] == "string"

    def test_ag_neighbors_has_min_confidence(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_neighbors")["input_schema"]["properties"]
        assert "min_confidence" in props
        assert props["min_confidence"]["type"] == "number"

    def test_ag_neighbors_still_has_id(self, manifest: dict) -> None:
        """Backwards compat: 'id' remains required."""
        schema = _tool_by_name(manifest, "ag_neighbors")["input_schema"]
        assert "id" in schema["properties"]
        assert "id" in schema.get("required", [])

    def test_ag_neighbors_still_has_depth(self, manifest: dict) -> None:
        props = _tool_by_name(manifest, "ag_neighbors")["input_schema"]["properties"]
        assert "depth" in props


# ── T069: mcp_inventory and build_command ─────────────────────────────


class TestMcpInventoryList:
    def test_list_in_all_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import ALL_TOOLS
        assert "list" in ALL_TOOLS

    def test_list_in_read_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import READ_TOOLS
        assert "list" in READ_TOOLS


class TestBuildCommandList:
    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        mod = _load_adapter_module()
        self.build_command = mod.build_command

    def test_build_command_list_basic(self) -> None:
        argv = self.build_command("list", {"type": "commit", "limit": "10"})
        assert argv[0] == "auditgraph"
        assert argv[1] == "list"
        assert "--type" in argv
        assert "commit" in argv
        assert "--limit" in argv
        assert "10" in argv

    def test_build_command_list_produces_correct_argv(self) -> None:
        argv = self.build_command("list", {"type": "commit"})
        assert argv == ["auditgraph", "list", "--type", "commit"]

    def test_build_command_list_with_group_by(self) -> None:
        argv = self.build_command("list", {"group_by": "type"})
        assert "--group-by" in argv
        assert "type" in argv

    def test_build_command_list_with_count(self) -> None:
        argv = self.build_command("list", {"count": "true"})
        assert "--count" in argv

    def test_build_command_list_empty_payload(self) -> None:
        argv = self.build_command("list", {})
        assert argv == ["auditgraph", "list"]


# ── T069: backwards compat for existing tools ────────────────────────


class TestBackwardsCompat:
    def test_ag_query_command_unchanged(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_query")
        assert tool["command"] == "query"

    def test_ag_neighbors_command_unchanged(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_neighbors")
        assert tool["command"] == "neighbors"

    def test_ag_node_schema_unchanged(self, manifest: dict) -> None:
        tool = _tool_by_name(manifest, "ag_node")
        assert "id" in tool["input_schema"]["properties"]
        assert "id" in tool["input_schema"].get("required", [])

    def test_existing_tool_count_at_least_20(self, manifest: dict) -> None:
        """We had 20 tools before, now 21+ with ag_list."""
        assert len(manifest["tools"]) >= 21
