from __future__ import annotations

from pathlib import Path

from auditgraph.config import Config, load_config
from auditgraph.utils.redaction import build_redactor_for_pkg_root

from auditgraph.storage.artifacts import write_text
from auditgraph.storage.loaders import load_entities


def export_graphml(pkg_root: Path, output_path: Path, config: Config | None = None) -> Path:
    resolved = config or load_config(None)
    redactor = build_redactor_for_pkg_root(pkg_root, resolved)
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\">",
        "  <graph id=\"auditgraph\" edgedefault=\"directed\">",
    ]
    for entity in load_entities(pkg_root, sorted_by_id=True):
        node_id = str(entity.get("id"))
        label = str(entity.get("name", node_id))
        label = str(redactor.redact_text(label).value)
        lines.append(f"    <node id=\"{node_id}\"><data key=\"label\">{label}</data></node>")
    lines.append("  </graph>")
    lines.append("</graphml>")
    write_text(output_path, "\n".join(lines))
    return output_path
