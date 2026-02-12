from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from auditgraph.utils.mcp_errors import ERROR_CODES, normalize_error
from auditgraph.utils.mcp_inventory import READ_TOOLS


def _load_module(path: Path, name: str):
    if not path.exists():
        raise AssertionError(f"Missing module at {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_manifest(manifest_path: Path) -> dict:
    import json

    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_mcp_tool_list_matches_manifest(manifest_path: Path) -> None:
    server_path = manifest_path.parent / "mcp" / "server.py"
    server = _load_module(server_path, "mcp_server")
    assert hasattr(server, "list_tools")

    manifest = _load_manifest(manifest_path)
    tool_list = server.list_tools(manifest)
    assert sorted(tool_list) == sorted(tool["name"] for tool in manifest["tools"])


def test_error_normalization_maps_codes() -> None:
    payload = normalize_error("INVALID_INPUT", "bad")
    assert payload["code"] == "INVALID_INPUT"
    fallback = normalize_error("BOGUS", "bad")
    assert fallback["code"] == "INTERNAL_ERROR"


def test_minimum_error_codes_present() -> None:
    required = {
        "INVALID_INPUT",
        "NOT_FOUND",
        "CONFLICT",
        "UNAUTHORIZED",
        "FORBIDDEN",
        "TIMEOUT",
        "RATE_LIMITED",
        "UPSTREAM_ERROR",
        "INTERNAL_ERROR",
    }
    assert set(ERROR_CODES) == required


def test_read_only_env_var_enforced(monkeypatch: pytest.MonkeyPatch, manifest_path: Path) -> None:
    server_path = manifest_path.parent / "mcp" / "server.py"
    server = _load_module(server_path, "mcp_server")
    assert hasattr(server, "is_read_only")

    monkeypatch.setenv("READ_ONLY", "1")
    assert server.is_read_only()

    monkeypatch.setenv("READ_ONLY", "0")
    assert not server.is_read_only()


def test_path_constraint_enforcement(manifest_path: Path) -> None:
    adapter_path = manifest_path.parent / "mcp" / "adapters" / "project.py"
    adapter = _load_module(adapter_path, "mcp_adapter")
    assert hasattr(adapter, "validate_output_path")

    adapter.validate_output_path("exports/graph.json")
    with pytest.raises(ValueError):
        adapter.validate_output_path("/tmp/graph.json")


def test_tool_logging_payload_has_required_fields(manifest_path: Path) -> None:
    server_path = manifest_path.parent / "mcp" / "server.py"
    server = _load_module(server_path, "mcp_server")
    assert hasattr(server, "build_log_payload")

    payload = server.build_log_payload(
        request_id="req-1",
        tool_name="ag_version",
        duration_ms=12.0,
        status="ok",
    )
    assert payload["request_id"] == "req-1"
    assert payload["tool_name"] == "ag_version"
    assert payload["duration_ms"] == 12.0
    assert payload["status"] == "ok"


def test_read_tool_timeout_smoke(manifest_path: Path) -> None:
    manifest = _load_manifest(manifest_path)
    by_command = {tool["command"]: tool for tool in manifest["tools"]}
    for command in READ_TOOLS:
        tool = by_command[command]
        assert tool["timeout_ms"] <= 5000
