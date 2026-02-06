from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json, write_text


def _load_entities(pkg_root: Path) -> list[dict[str, object]]:
    entities_dir = pkg_root / "entities"
    entities: list[dict[str, object]] = []
    if not entities_dir.exists():
        return entities
    for path in entities_dir.rglob("*.json"):
        entities.append(read_json(path))
    return sorted(entities, key=lambda item: str(item.get("id", "")))


def export_graphml(pkg_root: Path, output_path: Path) -> Path:
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\">",
        "  <graph id=\"auditgraph\" edgedefault=\"directed\">",
    ]
    for entity in _load_entities(pkg_root):
        node_id = str(entity.get("id"))
        label = str(entity.get("name", node_id))
        lines.append(f"    <node id=\"{node_id}\"><data key=\"label\">{label}</data></node>")
    lines.append("  </graph>")
    lines.append("</graphml>")
    write_text(output_path, "\n".join(lines))
    return output_path
