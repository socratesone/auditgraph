"""Spec 027 User Story 2 — MCP payload validation (FR-005..FR-009, FR-007 env).

Every incoming tool-call payload MUST be validated against its declared
input_schema before any subprocess is spawned. Rejections return a
structured envelope and never echo the rejected value.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "llm-tooling" / "tool.manifest.json"
SERVER_PATH = REPO_ROOT / "llm-tooling" / "mcp" / "server.py"
VALIDATION_PATH = REPO_ROOT / "llm-tooling" / "mcp" / "validation.py"


# Tools whose validation coverage is explicitly acknowledged by the maintainer.
# This frozenset is the inventory guard required by FR-009 — adding a new tool
# to tool.manifest.json without also adding it here must fail the suite.
EXPECTED_TESTED_TOOLS: frozenset[str] = frozenset(
    {
        "ag_version",
        "ag_query",
        "ag_node",
        "ag_neighbors",
        "ag_diff",
        "ag_jobs_list",
        "ag_why_connected",
        "ag_init",
        "ag_ingest",
        "ag_import",
        "ag_normalize",
        "ag_extract",
        "ag_link",
        "ag_index",
        "ag_rebuild",
        "ag_export",
        "ag_jobs_run",
        "ag_list",
        "ag_validate_store",
        "git_who_changed",
        "git_commits_for_file",
        "git_file_introduced",
        "git_file_history",
    }
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server_module():
    return _load_module(SERVER_PATH, "mcp_server_under_test")


@pytest.fixture
def validation_module():
    return _load_module(VALIDATION_PATH, "mcp_validation_under_test")


@pytest.fixture
def manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _tool_by_name(manifest: dict, name: str) -> dict:
    for tool in manifest["tools"]:
        if tool["name"] == name:
            return tool
    raise KeyError(name)


def _mock_adapter_never_called():
    """Build an adapter mock that fails if run_command is invoked."""
    adapter = MagicMock()
    adapter.build_command = MagicMock(side_effect=AssertionError("build_command must not be called on validation failure"))
    adapter.run_command = MagicMock(side_effect=AssertionError("run_command must not be called on validation failure"))
    adapter.validate_output_path = MagicMock()
    return adapter


def test_rejects_unknown_key(server_module):
    adapter = _mock_adapter_never_called()
    with patch.object(server_module, "_load_adapter", return_value=adapter):
        result = server_module.execute_tool("ag_version", {"unknown_key": "value"})
    assert "error" in result
    err = result["error"]
    assert err["code"] == "validation_failed"
    assert err["tool"] == "ag_version"
    assert err["field"] == ""
    assert err["reason"].startswith("unknown property")
    adapter.run_command.assert_not_called()
    adapter.build_command.assert_not_called()


def test_rejects_type_mismatch(server_module):
    adapter = _mock_adapter_never_called()
    with patch.object(server_module, "_load_adapter", return_value=adapter):
        result = server_module.execute_tool("ag_query", {"q": 42})
    assert "error" in result
    err = result["error"]
    assert err["code"] == "validation_failed"
    assert err["tool"] == "ag_query"
    assert err["field"] == "/q"
    assert err["reason"].startswith("expected string")
    # Rejected instance value MUST NOT be echoed
    dumped = json.dumps(result)
    assert "42" not in dumped or '"tool"' in dumped  # allow incidental digits in other keys
    # Stronger: the substring "42" should not appear inside the reason
    assert "42" not in err["reason"]


def test_rejects_oversized_string(server_module, validation_module):
    adapter = _mock_adapter_never_called()
    oversize = "A" * (validation_module.DEFAULT_MAX_STRING_LENGTH + 1)
    with patch.object(server_module, "_load_adapter", return_value=adapter):
        result = server_module.execute_tool("ag_query", {"q": oversize})
    assert "error" in result
    err = result["error"]
    assert err["reason"].startswith("exceeds maxLength")
    # The 5000+ A's MUST NOT appear anywhere in the envelope
    assert "AAAA" not in json.dumps(result)


def test_positive_case_still_passes(server_module):
    adapter = MagicMock()
    adapter.build_command = MagicMock(return_value=["auditgraph", "version"])
    adapter.run_command = MagicMock(return_value={"version": "test"})
    adapter.validate_output_path = MagicMock()
    with patch.object(server_module, "_load_adapter", return_value=adapter):
        result = server_module.execute_tool("ag_version", {})
    assert "error" not in result
    adapter.run_command.assert_called_once()


def test_every_tool_has_validation_coverage(server_module, manifest):
    manifest_tools = {t["name"] for t in manifest["tools"]}
    symmetric = manifest_tools.symmetric_difference(EXPECTED_TESTED_TOOLS)
    assert symmetric == set(), (
        f"tool.manifest.json and EXPECTED_TESTED_TOOLS drift: {sorted(symmetric)}. "
        "Add the new tool to EXPECTED_TESTED_TOOLS in this test file AFTER "
        "confirming it rejects adversarial payloads."
    )

    for tool_name in sorted(EXPECTED_TESTED_TOOLS):
        tool = _tool_by_name(manifest, tool_name)
        schema = tool.get("input_schema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # 1) Unknown-key rejection — build a payload with all required properties
        # filled with plausible values plus an extra bogus key.
        base: dict = {}
        for req in required:
            prop = properties.get(req, {})
            ptype = prop.get("type", "string")
            if ptype == "string":
                base[req] = "x"
            elif ptype == "integer":
                base[req] = 1
            elif ptype == "array":
                base[req] = []
            elif ptype == "object":
                base[req] = {}
            elif ptype == "boolean":
                base[req] = False
            else:
                base[req] = "x"
        payload_unknown = {**base, "__injected_key__": "value"}
        adapter = _mock_adapter_never_called()
        with patch.object(server_module, "_load_adapter", return_value=adapter):
            result = server_module.execute_tool(tool_name, payload_unknown)
        assert "error" in result, f"{tool_name} accepted unknown key"
        assert result["error"]["code"] == "validation_failed"
        assert result["error"]["reason"].startswith("unknown property"), (
            f"{tool_name}: reason={result['error']['reason']}"
        )
        adapter.run_command.assert_not_called()

        # 2) Type-mismatch (only meaningful if there is at least one string prop)
        string_props = [k for k, v in properties.items() if v.get("type") == "string"]
        if string_props:
            target = string_props[0]
            payload_type = {**base, target: 12345}
            adapter = _mock_adapter_never_called()
            with patch.object(server_module, "_load_adapter", return_value=adapter):
                result = server_module.execute_tool(tool_name, payload_type)
            assert "error" in result, f"{tool_name} accepted int for string {target}"
            assert result["error"]["reason"].startswith("expected string"), (
                f"{tool_name}: reason={result['error']['reason']}"
            )
            adapter.run_command.assert_not_called()

            # 3) Oversized-string
            payload_big = {**base, target: "B" * 5000}
            adapter = _mock_adapter_never_called()
            with patch.object(server_module, "_load_adapter", return_value=adapter):
                result = server_module.execute_tool(tool_name, payload_big)
            assert "error" in result, f"{tool_name} accepted oversized string"
            assert result["error"]["reason"].startswith("exceeds maxLength"), (
                f"{tool_name}: reason={result['error']['reason']}"
            )
            adapter.run_command.assert_not_called()


def test_rejection_does_not_echo_instance(server_module):
    """A payload carrying a secret-shaped value MUST NOT appear in the envelope."""
    sentinel = "SENTINEL_XYZ_DO_NOT_ECHO_ME"
    adapter = _mock_adapter_never_called()
    payload = {"q": f"password={sentinel}" + "A" * 5000}
    with patch.object(server_module, "_load_adapter", return_value=adapter):
        result = server_module.execute_tool("ag_query", payload)
    assert "error" in result
    assert sentinel not in json.dumps(result)


def test_max_string_length_configurable(monkeypatch, validation_module):
    """FR-007: DEFAULT_MAX_STRING_LENGTH is 4096 and is overridable via env var.

    Zero, negative, or non-numeric values raise ConfigurationError.
    """
    assert validation_module.DEFAULT_MAX_STRING_LENGTH == 4096

    # Override works
    monkeypatch.setenv("AUDITGRAPH_MCP_MAX_STRING_LENGTH", "1024")
    assert validation_module.resolve_max_string_length() == 1024

    # Zero rejected
    monkeypatch.setenv("AUDITGRAPH_MCP_MAX_STRING_LENGTH", "0")
    with pytest.raises(validation_module.ConfigurationError):
        validation_module.resolve_max_string_length()

    # Negative rejected
    monkeypatch.setenv("AUDITGRAPH_MCP_MAX_STRING_LENGTH", "-1")
    with pytest.raises(validation_module.ConfigurationError):
        validation_module.resolve_max_string_length()

    # Non-numeric rejected
    monkeypatch.setenv("AUDITGRAPH_MCP_MAX_STRING_LENGTH", "not_a_number")
    with pytest.raises(validation_module.ConfigurationError):
        validation_module.resolve_max_string_length()

    # Cleanup — unset yields default
    monkeypatch.delenv("AUDITGRAPH_MCP_MAX_STRING_LENGTH", raising=False)
    assert validation_module.resolve_max_string_length() == 4096
