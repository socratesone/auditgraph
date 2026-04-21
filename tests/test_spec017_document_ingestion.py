from __future__ import annotations

import shutil
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.ingest.parsers import parse_file
from tests.support import null_parse_options
from auditgraph.ingest.policy import load_policy
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, read_json
from auditgraph.storage.hashing import deterministic_document_id
from tests.support import spec017_fixture_dir


def _copy_fixture_tree(target_root: Path) -> Path:
    fixture_dir = spec017_fixture_dir()
    docs_dir = target_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name in ("sample.pdf", "scanned.pdf", "sample.docx"):
        shutil.copy2(fixture_dir / name, docs_dir / name)
    return docs_dir


def test_spec017_parser_selection_and_unsupported_doc(tmp_path: Path) -> None:
    docs_dir = _copy_fixture_tree(tmp_path)
    unsupported = docs_dir / "legacy.doc"
    unsupported.write_text("legacy binary placeholder", encoding="utf-8")

    policy = load_policy(load_config(None).profile())

    pdf_result = parse_file(docs_dir / "sample.pdf", policy, null_parse_options())
    assert pdf_result.parser_id == "document/pdf"

    docx_result = parse_file(docs_dir / "sample.docx", policy, null_parse_options())
    assert docx_result.parser_id == "document/docx"

    doc_result = parse_file(unsupported, policy, null_parse_options())
    assert doc_result.status == "failed"
    assert doc_result.status_reason == "unsupported_doc_format"


def test_spec017_deterministic_normalization_and_chunk_boundaries(tmp_path: Path) -> None:
    docs_dir = _copy_fixture_tree(tmp_path)
    policy = load_policy(load_config(None).profile())
    options: dict[str, object] = {"chunk_tokens": 4, "chunk_overlap_tokens": 1}

    first = parse_file(docs_dir / "sample.docx", policy, {**null_parse_options(), **options})
    second = parse_file(docs_dir / "sample.docx", policy, {**null_parse_options(), **options})
    assert first.text == second.text

    first_raw = first.metadata.get("chunks", []) if isinstance(first.metadata, dict) else []
    second_raw = second.metadata.get("chunks", []) if isinstance(second.metadata, dict) else []
    first_chunks = first_raw if isinstance(first_raw, list) else []
    second_chunks = second_raw if isinstance(second_raw, list) else []
    assert first_chunks == second_chunks
    assert len(first_chunks) >= 2
    second_chunk = first_chunks[1] if isinstance(first_chunks[1], dict) else {}
    assert second_chunk.get("overlap_tokens") == 1


def test_spec017_unchanged_hash_skip_reason(tmp_path: Path) -> None:
    """Spec-028 migration: cache hits are `parse_status="ok"` + `source_origin="cached"`.

    Pre-028 this test asserted `parse_status="skipped"` for cache hits — that
    shape was explicitly retired by Spec-028 FR-001/FR-002 because it caused
    BUG-1 (cache hits starving the extract stage). The observability signal
    (`status_reason` / `skip_reason` = "unchanged_source_hash") is preserved
    on the record for audit purposes, but the filtering signal
    (`parse_status`) now correctly says "ok" — a cache hit is a successful
    parse reused from cache, not a skip.
    """
    docs_dir = _copy_fixture_tree(tmp_path)
    runner = PipelineRunner()
    config = load_config(None)

    first = runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])
    assert first.status == "ok"

    second = runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])
    manifest = read_json(Path(second.detail["manifest"]))
    cached = [
        record
        for record in manifest["records"]
        if record.get("source_origin") == "cached"
    ]
    assert cached, "second run must have at least one cache hit for this fixture"
    assert all(record["parse_status"] == "ok" for record in cached), (
        "Spec-028 FR-001: cache hits are ok, not skipped"
    )
    assert all(record.get("status_reason") == "unchanged_source_hash" for record in cached), (
        "observability signal preserved for audit"
    )
    assert all(record.get("skip_reason") == "unchanged_source_hash" for record in cached)


def test_spec017_ocr_mode_matrix(tmp_path: Path) -> None:
    docs_dir = _copy_fixture_tree(tmp_path)
    policy = load_policy(load_config(None).profile())

    off = parse_file(docs_dir / "scanned.pdf", policy, {**null_parse_options(), **{"ocr_mode": "off"}})
    assert off.status == "failed"
    assert off.status_reason == "ocr_required"

    auto = parse_file(docs_dir / "scanned.pdf", policy, {**null_parse_options(), **{"ocr_mode": "auto"}})
    assert auto.status == "failed"
    assert auto.status_reason == "ocr_engine_unavailable"

    on = parse_file(docs_dir / "scanned.pdf", policy, {**null_parse_options(), **{"ocr_mode": "on"}})
    assert on.status == "failed"
    assert on.status_reason == "ocr_engine_unavailable"


def test_spec017_overwrite_in_place_hash_history(tmp_path: Path) -> None:
    docs_dir = _copy_fixture_tree(tmp_path)
    runner = PipelineRunner()
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)

    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir / "sample.pdf")])

    pdf_path = docs_dir / "sample.pdf"
    original = pdf_path.read_bytes()
    pdf_path.write_bytes(original.replace(b"Sample PDF text layer.", b"Updated PDF text layer"))

    runner.run_import(root=tmp_path, config=config, targets=[str(pdf_path)])

    document_id = deterministic_document_id(pdf_path.as_posix())
    document = read_json(pkg_root / "documents" / f"{document_id}.json")
    history = document.get("hash_history", [])
    assert len(history) >= 2
    assert document.get("source_hash") in history
