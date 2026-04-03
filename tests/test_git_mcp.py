"""T047: Tests for git provenance MCP tool definitions.

Verifies:
- tool.manifest.json contains entries for all 4 git query tools
- Each manifest entry has required fields: name, description, command, risk, idempotent, examples
- Input schemas require a 'file' string parameter matching FileInput contract
- Tool commands appear in mcp_inventory.py READ_TOOLS
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# --- Manifest tests ---

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "llm-tooling" / "tool.manifest.json"

GIT_TOOLS = [
    {
        "name": "git_who_changed",
        "command": "git-who",
        "description_contains": "who",
    },
    {
        "name": "git_commits_for_file",
        "command": "git-log",
        "description_contains": "commit",
    },
    {
        "name": "git_file_introduced",
        "command": "git-introduced",
        "description_contains": "introduced",
    },
    {
        "name": "git_file_history",
        "command": "git-history",
        "description_contains": "history",
    },
]


@pytest.fixture
def manifest() -> dict:
    """Load the tool manifest."""
    with open(MANIFEST_PATH) as f:
        return json.load(f)


@pytest.fixture
def manifest_tools(manifest: dict) -> dict[str, dict]:
    """Build a name -> tool dict from manifest."""
    return {t["name"]: t for t in manifest["tools"]}


class TestGitToolManifestEntries:
    """Each git query tool must exist in the manifest with correct structure."""

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_exists_in_manifest(self, manifest_tools: dict, tool_spec: dict) -> None:
        assert tool_spec["name"] in manifest_tools, (
            f"Tool '{tool_spec['name']}' not found in manifest"
        )

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_has_required_fields(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        required_fields = ["name", "description", "command", "risk", "idempotency", "examples"]
        for field in required_fields:
            assert field in tool, f"Tool '{tool_spec['name']}' missing field '{field}'"

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_command_matches(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        assert tool["command"] == tool_spec["command"]

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_risk_is_low(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        assert tool["risk"] == "low", f"Git query tools should be low risk (READ)"

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_is_idempotent(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        assert tool["idempotency"] == "idempotent"

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_has_examples(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        assert len(tool["examples"]) > 0

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_tool_description_relevant(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        assert tool_spec["description_contains"].lower() in tool["description"].lower()


class TestGitToolInputSchema:
    """Each git query tool must require a 'file' string input matching FileInput contract."""

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_input_schema_has_file_property(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        schema = tool["input_schema"]
        assert "properties" in schema
        assert "file" in schema["properties"]
        assert schema["properties"]["file"]["type"] == "string"

    @pytest.mark.parametrize(
        "tool_spec",
        GIT_TOOLS,
        ids=[t["name"] for t in GIT_TOOLS],
    )
    def test_input_schema_file_is_required(self, manifest_tools: dict, tool_spec: dict) -> None:
        tool = manifest_tools.get(tool_spec["name"])
        if tool is None:
            pytest.skip(f"Tool '{tool_spec['name']}' not in manifest yet")
        schema = tool["input_schema"]
        assert "required" in schema
        assert "file" in schema["required"]


class TestGitToolsInInventory:
    """Git query tool commands must appear in mcp_inventory READ_TOOLS."""

    def test_git_who_in_read_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import READ_TOOLS
        assert "git-who" in READ_TOOLS

    def test_git_log_in_read_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import READ_TOOLS
        assert "git-log" in READ_TOOLS

    def test_git_introduced_in_read_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import READ_TOOLS
        assert "git-introduced" in READ_TOOLS

    def test_git_history_in_read_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import READ_TOOLS
        assert "git-history" in READ_TOOLS

    def test_git_tools_in_all_tools(self) -> None:
        from auditgraph.utils.mcp_inventory import ALL_TOOLS
        for cmd in ["git-who", "git-log", "git-introduced", "git-history"]:
            assert cmd in ALL_TOOLS, f"'{cmd}' not in ALL_TOOLS"
