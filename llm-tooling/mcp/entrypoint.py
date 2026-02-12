"""MCP stdio server entrypoint for auditgraph tooling."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_server_module():
    server_path = Path(__file__).resolve().parent / "server.py"
    spec = importlib.util.spec_from_file_location("auditgraph_mcp_server", server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load MCP server module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_headers() -> dict[str, str] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.readline()
        if line == "":
            return None
        line = line.strip("\r\n")
        if not line:
            return headers
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()


def _read_message() -> dict[str, Any] | None:
    headers = _read_headers()
    if headers is None:
        return None
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.read(length)
    if not body:
        return None
    return json.loads(body)


def _send_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload)
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
    sys.stdout.flush()


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _jsonrpc_result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _build_tool_list(manifest: dict) -> list[dict[str, Any]]:
    tools = []
    for tool in manifest.get("tools", []):
        tools.append(
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "inputSchema": tool.get("input_schema", {}),
            }
        )
    return tools


def main() -> None:
    server = _load_server_module()
    manifest = server.load_manifest()

    while True:
        message = _read_message()
        if message is None:
            break
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "auditgraph-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            }
            _send_message(_jsonrpc_result(msg_id, result))
            continue

        if method == "tools/list":
            result = {"tools": _build_tool_list(manifest)}
            _send_message(_jsonrpc_result(msg_id, result))
            continue

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not tool_name:
                _send_message(_jsonrpc_error(msg_id, -32602, "Missing tool name"))
                continue
            payload = server.execute_tool(tool_name, arguments)
            is_error = "error" in payload
            content = [{"type": "text", "text": json.dumps(payload)}]
            result = {"content": content, "isError": is_error}
            _send_message(_jsonrpc_result(msg_id, result))
            continue

        _send_message(_jsonrpc_error(msg_id, -32601, f"Unknown method: {method}"))


if __name__ == "__main__":
    main()
