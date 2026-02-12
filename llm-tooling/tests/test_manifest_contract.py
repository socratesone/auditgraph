from __future__ import annotations

import json
from pathlib import Path

import yaml

from auditgraph.utils.mcp_inventory import ALL_TOOLS


def _load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_schema_required(path: Path) -> tuple[set[str], set[str]]:
    with path.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    schemas = spec["components"]["schemas"]
    manifest_required = set(schemas["ToolManifest"].get("required", []))
    tool_required = set(schemas["ToolDefinition"].get("required", []))
    return manifest_required, tool_required


def test_manifest_matches_contract_schema(manifest_path: Path) -> None:
    contract_path = (
        Path(__file__).resolve().parents[1]
        / ".."
        / "specs"
        / "016-mcp-tools-llm-integration"
        / "contracts"
        / "tool-manifest.openapi.yaml"
    ).resolve()
    manifest_required, tool_required = _load_schema_required(contract_path)

    manifest = _load_manifest(manifest_path)
    assert manifest_required.issubset(manifest.keys())

    tools = manifest.get("tools", [])
    assert isinstance(tools, list)
    assert tools, "Manifest tools list must not be empty"

    for tool in tools:
        assert tool_required.issubset(tool.keys())


def test_manifest_covers_cli_inventory(manifest_path: Path) -> None:
    manifest = _load_manifest(manifest_path)
    commands = {tool.get("command") for tool in manifest.get("tools", [])}
    assert None not in commands, "Each tool must include a command string"
    assert set(ALL_TOOLS) == commands


def test_manifest_examples_risk_idempotency(manifest_path: Path) -> None:
    manifest = _load_manifest(manifest_path)
    tools = manifest.get("tools", [])
    assert tools

    allowed_risk = {"low", "medium", "high"}
    allowed_idempotency = {"idempotent", "non-idempotent", "unknown"}

    for tool in tools:
        assert tool.get("risk") in allowed_risk
        assert tool.get("idempotency") in allowed_idempotency
        examples = tool.get("examples", [])
        assert isinstance(examples, list)
        assert examples, "Each tool must provide at least one example"
