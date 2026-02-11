from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.ranking import apply_ranking
from auditgraph.storage.artifacts import read_json, profile_pkg_root
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION
from auditgraph.storage.hashing import deterministic_run_id, inputs_hash, outputs_hash
from auditgraph.storage.manifests import IngestRecord


def test_hashes_are_deterministic() -> None:
    records_a = [
        IngestRecord(
            path="notes/a.md",
            source_hash="hash_a",
            size=1,
            mtime=1.0,
            parser_id="text/markdown",
            parse_status="ok",
        ),
        IngestRecord(
            path="notes/b.md",
            source_hash="hash_b",
            size=1,
            mtime=1.0,
            parser_id="text/markdown",
            parse_status="ok",
        ),
    ]
    records_b = list(reversed(records_a))

    assert inputs_hash(records_a) == inputs_hash(records_b)
    assert outputs_hash(records_a) == outputs_hash(records_b)

    run_id_a = deterministic_run_id(inputs_hash(records_a), "cfg")
    run_id_b = deterministic_run_id(inputs_hash(records_b), "cfg")

    assert run_id_a == run_id_b


def test_ingest_writes_provenance_index(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text("# Note", encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)

    manifest = read_json(Path(result.detail["manifest"]))
    run_id = manifest["run_id"]
    assert manifest["schema_version"] == ARTIFACT_SCHEMA_VERSION
    provenance_path = profile_pkg_root(tmp_path, config) / "provenance" / f"{run_id}.json"

    assert provenance_path.exists()
    records = read_json(provenance_path)
    assert records


def test_ranking_tie_break_is_stable() -> None:
    ranked = apply_ranking(
        [
            {"id": "b", "score": 1.0, "explanation": {"tie_break": ["b"]}},
            {"id": "a", "score": 1.0, "explanation": {"tie_break": ["a"]}},
        ],
        rounding=0.0,
    )

    assert [item["id"] for item in ranked] == ["a", "b"]
