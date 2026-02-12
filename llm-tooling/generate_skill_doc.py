"""Generate skill documentation from the tool manifest."""

from __future__ import annotations

import json
from pathlib import Path

from auditgraph.utils.mcp_manifest import load_manifest


def _format_example(example: dict) -> str:
    return json.dumps(example, indent=2)


def generate_skill_doc(manifest: dict) -> str:
    tools = sorted(manifest.get("tools", []), key=lambda item: item.get("name", ""))
    lines: list[str] = [
        "# Auditgraph Skill",
        "",
        "This document describes the MCP tool surface for auditgraph.",
        "",
    ]
    for tool in tools:
        lines.append(f"## {tool['name']}")
        lines.append("")
        lines.append(tool.get("description", ""))
        lines.append("")
        lines.append(f"- Risk: {tool.get('risk')}")
        lines.append(f"- Idempotency: {tool.get('idempotency')}")
        lines.append("")
        lines.append("### Inputs")
        lines.append("```")
        lines.append(json.dumps(tool.get("input_schema", {}), indent=2))
        lines.append("```")
        lines.append("")
        lines.append("### Outputs")
        lines.append("```")
        lines.append(json.dumps(tool.get("output_schema", {}), indent=2))
        lines.append("```")
        lines.append("")
        lines.append("### Example")
        example = (tool.get("examples") or [{}])[0]
        lines.append("```")
        lines.append(_format_example(example))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    manifest = load_manifest()
    content = generate_skill_doc(manifest)
    output_path = Path(__file__).resolve().parent / "skill.md"
    output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
