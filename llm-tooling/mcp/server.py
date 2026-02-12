"""MCP server utilities for auditgraph tooling."""

from __future__ import annotations

import importlib.util
import logging
import os
import time
from pathlib import Path
from typing import Any

from auditgraph.utils.mcp_errors import normalize_error
from auditgraph.utils.mcp_manifest import load_manifest

logger = logging.getLogger(__name__)


def _load_adapter():
    adapter_path = Path(__file__).resolve().parent / "adapters" / "project.py"
    spec = importlib.util.spec_from_file_location("mcp_project_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load project adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_tools(manifest: dict) -> list[str]:
    return [tool["name"] for tool in manifest.get("tools", [])]


def is_read_only() -> bool:
    return os.getenv("READ_ONLY") == "1"


def build_log_payload(*, request_id: str, tool_name: str, duration_ms: float, status: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "status": status,
    }


def _find_tool(manifest: dict, tool_name: str) -> dict:
    for tool in manifest.get("tools", []):
        if tool.get("name") == tool_name:
            return tool
    raise KeyError(f"Unknown tool: {tool_name}")


def _enforce_read_only(tool: dict) -> None:
    if not is_read_only():
        return
    if not tool.get("constraints", {}).get("read_only_safe", False):
        raise PermissionError("FORBIDDEN")


def execute_tool(tool_name: str, payload: dict) -> dict:
    manifest = load_manifest()
    tool = _find_tool(manifest, tool_name)
    request_id = payload.get("request_id", "req-unknown")

    start = time.monotonic()
    try:
        _enforce_read_only(tool)
        if tool.get("command") == "export" and payload.get("output"):
            adapter = _load_adapter()
            adapter.validate_output_path(payload["output"])
        adapter = _load_adapter()
        argv = adapter.build_command(tool["command"], payload)
        result = adapter.run_command(argv)
        status = "ok"
    except Exception as exc:  # pragma: no cover - will be refined during tests
        result = {"error": normalize_error(type(exc).__name__, str(exc))}
        status = "error"
    duration_ms = (time.monotonic() - start) * 1000
    logger.info("tool_event", extra=build_log_payload(
        request_id=request_id,
        tool_name=tool_name,
        duration_ms=duration_ms,
        status=status,
    ))
    return result
