# Auditgraph MCP Guide (VS Code Copilot)

This guide explains how to run auditgraph as an MCP server and connect it to VS Code Copilot.

## What you need

- Python 3.10+
- A working auditgraph checkout
- VS Code with Copilot Chat support

## 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Generate MCP artifacts (optional if already generated)

```bash
python llm-tooling/generate_skill_doc.py
python llm-tooling/generate_adapters.py
```

## 3) Start the MCP server (optional)

When VS Code is configured with `mcp.json`, it starts the server automatically.
You only need to run the entrypoint manually for debugging.

```bash
python llm-tooling/mcp/entrypoint.py
```

To enable read-only mode:

```bash
READ_ONLY=1 python llm-tooling/mcp/entrypoint.py
```

## 4) Configure VS Code to use the MCP server

VS Code stores MCP server configuration in `mcp.json` (not `settings.json`).

Open the configuration file from the Command Palette:

- `MCP: Open User Configuration` (applies to all workspaces)
- `MCP: Open Workspace Folder Configuration` (writes `.vscode/mcp.json`)

Example `mcp.json` (workspace configuration):

```json
{
  "servers": {
    "auditgraph": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": [
        "-u",
        "${workspaceFolder}/llm-tooling/mcp/entrypoint.py"
      ],
      "env": {
        "READ_ONLY": "1"
      }
    }
  }
}
```

### Remote/Global setup (important)

If you are connected over Remote SSH, the MCP server is launched on the remote host.
That means the `mcp.json` entry must live in **Remote User Configuration**, not just
your local (Windows/macOS) user config. Use Command Palette:

- `MCP: Open User Configuration` while connected to the remote host
- Add the same `servers.auditgraph` entry there

To make auditgraph available in all workspaces on that remote host, keep the entry in
Remote User Configuration (global), not per-workspace configuration.

If you want this to work across unrelated projects, point `command` and `args` to a
stable auditgraph checkout path (or create a wrapper script on the remote host).
Keep `-u` to avoid stdio buffering issues.

```json
{
  "servers": {
    "auditgraph": {
      "type": "stdio",
      "command": "/path/to/auditgraph/.venv/bin/python",
      "args": [
        "-u",
        "/path/to/auditgraph/llm-tooling/mcp/entrypoint.py"
      ],
      "env": { "READ_ONLY": "0" }
    }
  }
}
```

## 5) Verify in Copilot Chat

After VS Code starts the MCP server, ask Copilot to list tools, for example:

- "List available auditgraph tools"
- "Run ag_version"

If the server is connected, Copilot should surface tool calls and results.

## Troubleshooting

- If Copilot does not see tools, run `MCP: List Servers`, select `auditgraph`, and use `Show Output`.
- If you are on Remote SSH and tools never appear, confirm the entry is in Remote User Configuration.
- If you see `ModuleNotFoundError: auditgraph`, verify you installed the package with `pip install -e .`.
- If tool calls fail, check `Show Output`, and confirm `READ_ONLY=1` is set when desired.
- If tools appear stale or missing, run `MCP: Reset Cached Tools` and restart the server.

## Notes

- The MCP server only exposes tools defined in `llm-tooling/tool.manifest.json`.
- Write tools are blocked when `READ_ONLY=1` is set.
- Output paths for export must be under `exports/`.
