"""Generate adapter bundles from the tool manifest."""

from __future__ import annotations

import json
from pathlib import Path

from auditgraph.utils.mcp_manifest import load_manifest


def generate_adapter_bundle(manifest: dict) -> dict:
    tools = sorted(manifest.get("tools", []), key=lambda item: item.get("name", ""))
    return {
        "format": "openai",
        "tools": [
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("input_schema", {}),
            }
            for tool in tools
        ],
    }


def main() -> None:
    manifest = load_manifest()
    bundle = generate_adapter_bundle(manifest)
    output_path = Path(__file__).resolve().parent / "adapters" / "openai.functions.json"
    output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
