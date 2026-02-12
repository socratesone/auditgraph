from __future__ import annotations

from pathlib import Path


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_manifest(path: Path) -> dict:
    import json

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_skill_doc_has_sections_for_all_tools(manifest_path: Path) -> None:
    skill_path = manifest_path.parent / "skill.md"
    content = _load_text(skill_path)
    manifest = _load_manifest(manifest_path)

    for tool in manifest.get("tools", []):
        header = f"## {tool['name']}"
        assert header in content
        assert "Example" in content
