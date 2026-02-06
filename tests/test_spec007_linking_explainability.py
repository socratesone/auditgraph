from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.extract.entities import build_note_entity
from auditgraph.extract.manifest import write_entities
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import read_json, profile_pkg_root


def test_link_stage_creates_adjacency(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("# Note", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    ingest = runner.run_ingest(root=tmp_path, config=config)
    run_id = read_json(Path(ingest.detail["manifest"]))["run_id"]
    runner.run_extract(root=tmp_path, config=config, run_id=run_id)

    pkg_root = profile_pkg_root(tmp_path, config)
    manifest = read_json(pkg_root / "runs" / run_id / "ingest-manifest.json")
    record = manifest["records"][0]
    extra_entity = build_note_entity("Extra", record["path"], record["source_hash"])
    write_entities(pkg_root, [extra_entity])

    link = runner.run_link(root=tmp_path, config=config, run_id=run_id)
    assert link.status == "ok"

    link_files = list((pkg_root / "links").rglob("*.json"))
    assert link_files
    link_payload = read_json(link_files[0])
    assert link_payload["rule_id"] == "link.source_cooccurrence.v1"
    assert link_payload["evidence"]

    adjacency = read_json(pkg_root / "indexes" / "graph" / "adjacency.json")
    assert adjacency
