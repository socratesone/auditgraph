"""MCP stdio server entrypoint for auditgraph tooling."""

from __future__ import annotations

import importlib.util
import json
import os
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


def _debug(message: str) -> None:
    log_path = os.getenv("MCP_LOG")
    if not log_path:
        return
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass


def _read_headers(first_line: bytes | None = None) -> dict[str, str] | None:
    headers: dict[str, str] = {}
    if first_line is not None:
        line = first_line.strip(b"\r\n")
        _debug(f"auditgraph-mcp: header line={line!r}")
        if line and b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode("ascii", "ignore").strip().lower()] = value.decode(
                "ascii", "ignore"
            ).strip()
        elif line == b"":
            return headers
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            _debug("auditgraph-mcp: stdin EOF")
            return None
        line = line.strip(b"\r\n")
        _debug(f"auditgraph-mcp: header line={line!r}")
        if not line:
            return headers
        if b":" not in line:
            continue
        key, value = line.split(b":", 1)
        headers[key.decode("ascii", "ignore").strip().lower()] = value.decode(
            "ascii", "ignore"
        ).strip()

def _read_message() -> dict[str, Any] | None:
    first_line = sys.stdin.buffer.readline()
    if first_line == b"":
        _debug("auditgraph-mcp: stdin EOF")
        return None
    line = first_line.strip(b"\r\n")
    if line.startswith(b"{"):
        _debug(f"auditgraph-mcp: json line={line!r}")
        return json.loads(line.decode("utf-8"))
    headers = _read_headers(first_line=first_line)
    if headers is None:
        return None
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _send_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(body + b"\n")
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
    _debug("auditgraph-mcp: entrypoint starting")
    server = _load_server_module()
    manifest = server.load_manifest()
    _debug("auditgraph-mcp: manifest loaded")

    while True:
        message = _read_message()
        if message is None:
            break
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if method == "initialize":
            _debug("auditgraph-mcp: initialize received")
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "auditgraph-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            }
            _send_message(_jsonrpc_result(msg_id, result))
            continue

        if method == "tools/list":
            _debug("auditgraph-mcp: tools/list received")
            result = {"tools": _build_tool_list(manifest)}
            _send_message(_jsonrpc_result(msg_id, result))
            continue

        if method == "tools/call":
            _debug("auditgraph-mcp: tools/call received")
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
