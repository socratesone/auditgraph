"""Subprocess adapter for auditgraph CLI tools."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

from auditgraph.utils.mcp_inventory import ALL_TOOLS

EXPORT_BASE = "exports"


def validate_output_path(output: str, base: str = EXPORT_BASE) -> None:
    if Path(output).is_absolute():
        raise ValueError("Output path must be relative to the workspace")
    normalized = Path(output).as_posix()
    if normalized == base or normalized.startswith(f"{base}/"):
        return
    raise ValueError(f"Output path must be under {base}/")


def _format_flag(name: str) -> str:
    return f"--{name.replace('_', '-') }"


def _apply_positional(command: str, payload: dict, argv: list[str]) -> None:
    if command == "import":
        argv.extend(payload.get("paths", []))
    if command == "node":
        argv.append(payload["id"])
    if command == "neighbors":
        argv.append(payload["id"])
    if command == "jobs run":
        argv.append(payload["name"])


def build_command(command: str, payload: dict) -> list[str]:
    if command not in ALL_TOOLS:
        raise ValueError(f"Unsupported command: {command}")

    argv = ["auditgraph", *command.split(" ")]
    _apply_positional(command, payload, argv)

    for key, value in payload.items():
        if key in {"paths", "id", "name"}:
            continue
        if value is None:
            continue
        argv.append(_format_flag(key))
        argv.append(str(value))

    return argv


def run_command(argv: Iterable[str]) -> dict:
    result = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    output = result.stdout.strip()
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"stdout": output, "status": "raw"}
    return {"status": "empty", "stderr": result.stderr.strip()}
