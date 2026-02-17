from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.neo4j.export import export_neo4j
from auditgraph.storage.artifacts import profile_pkg_root
from tests.fixtures.neo4j_fixtures import write_test_graph


def _normalize_export_text(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.startswith("// Timestamp:")]
    return "\n".join(lines)


def test_export_neo4j_writes_cypher_file(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)

    output_path = tmp_path / "exports" / "neo4j" / "graph.cypher"
    summary = export_neo4j(tmp_path, config, output_path=output_path)

    assert summary.mode == "export"
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert ":begin" in content
    assert "MERGE (n:Auditgraph" in content
    assert "MERGE (a)-[r:RELATES_TO" in content


def test_export_neo4j_is_deterministic_except_timestamp(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    write_test_graph(pkg_root)

    output_a = tmp_path / "exports" / "neo4j" / "a.cypher"
    output_b = tmp_path / "exports" / "neo4j" / "b.cypher"
    export_neo4j(tmp_path, config, output_path=output_a)
    export_neo4j(tmp_path, config, output_path=output_b)

    text_a = _normalize_export_text(output_a.read_text(encoding="utf-8"))
    text_b = _normalize_export_text(output_b.read_text(encoding="utf-8"))
    assert text_a == text_b
