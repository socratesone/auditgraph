"""Manifest loading and validation utilities for MCP tooling."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


def manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "llm-tooling" / "tool.manifest.json"


def contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "016-mcp-tools-llm-integration"
        / "contracts"
        / "tool-manifest.openapi.yaml"
    )


def load_manifest(path: Path | None = None) -> dict:
    path = path or manifest_path()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _required_fields() -> tuple[set[str], set[str]]:
    with contract_path().open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    schemas = spec["components"]["schemas"]
    manifest_required = set(schemas["ToolManifest"].get("required", []))
    tool_required = set(schemas["ToolDefinition"].get("required", []))
    return manifest_required, tool_required


def validate_manifest(manifest: dict) -> list[str]:
    """Return a list of validation errors for a manifest."""
    errors: list[str] = []
    manifest_required, tool_required = _required_fields()

    missing = manifest_required - set(manifest.keys())
    if missing:
        errors.append(f"Missing manifest fields: {sorted(missing)}")

    tools = manifest.get("tools", [])
    if not isinstance(tools, list) or not tools:
        errors.append("Manifest tools must be a non-empty list")
        return errors

    for idx, tool in enumerate(tools):
        if not isinstance(tool, dict):
            errors.append(f"Tool at index {idx} must be an object")
            continue
        tool_missing = tool_required - set(tool.keys())
        if tool_missing:
            errors.append(f"Tool {tool.get('name', idx)} missing fields: {sorted(tool_missing)}")

    return errors
