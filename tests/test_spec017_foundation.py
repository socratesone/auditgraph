from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.ingest.parsers import parse_file
from tests.support import null_parse_options
from auditgraph.ingest.policy import load_policy
from auditgraph.storage.config_snapshot import ingestion_config_hash
from auditgraph.utils.chunking import chunk_text
from auditgraph.utils.document_text import normalize_document_text
from tests.support import assert_spec017_fixture_checksums, ensure_spec017_fixtures, spec017_fixture_dir


def _runtime_dependencies_from_pyproject() -> set[str]:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    dependencies: set[str] = set()
    in_deps = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("dependencies") and "[" in line:
            in_deps = True
            continue
        if in_deps and line.startswith("]"):
            break
        if in_deps and line.startswith('"'):
            value = line.strip(",").strip('"')
            dependencies.add(value.split("=")[0].split("<")[0].split(">")[0])
    return dependencies


def _dependencies_from_requirements() -> set[str]:
    requirements = Path(__file__).resolve().parents[1] / "requirements-dev.txt"
    items: set[str] = set()
    for line in requirements.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or value.startswith("-e"):
            continue
        items.add(value.split("=")[0].split("<")[0].split(">")[0])
    return items


def test_spec017_dependency_consistency() -> None:
    runtime = _runtime_dependencies_from_pyproject()
    dev = _dependencies_from_requirements()
    for requirement in ("pypdf", "python-docx"):
        assert requirement in runtime
        assert requirement in dev


def test_spec017_fixture_manifest_checksums() -> None:
    ensure_spec017_fixtures()
    observed = assert_spec017_fixture_checksums()
    assert set(observed.keys()) == {"sample.pdf", "scanned.pdf", "sample.docx"}


def test_spec017_parser_routing_and_status_shape() -> None:
    fixture_dir = spec017_fixture_dir()
    policy = load_policy(load_config(None).profile())

    pdf_result = parse_file(fixture_dir / "sample.pdf", policy, null_parse_options())
    assert pdf_result.parser_id == "document/pdf"
    assert pdf_result.status in {"ok", "failed"}

    docx_result = parse_file(fixture_dir / "sample.docx", policy, null_parse_options())
    assert docx_result.parser_id == "document/docx"
    assert docx_result.status == "ok"

    unsupported_doc = fixture_dir / "unsupported.doc"
    unsupported_doc.write_text("legacy doc", encoding="utf-8")
    doc_result = parse_file(unsupported_doc, policy, null_parse_options())
    assert doc_result.status == "failed"
    assert doc_result.status_reason == "unsupported_doc_format"


def test_spec017_config_hash_and_helpers_are_deterministic() -> None:
    config = load_config(None)
    first = ingestion_config_hash(config)
    second = ingestion_config_hash(config)
    assert first == second

    normalized = normalize_document_text("line 1\r\nline 2\r\n\r\n")
    assert normalized == "line 1\nline 2"

    chunks = chunk_text("one two three four five six", chunk_size=3, overlap=1)
    assert [chunk["text"] for chunk in chunks] == ["one two three", "three four five", "five six"]
    assert chunks[1]["overlap_tokens"] == 1


def test_spec017_parse_metadata_contains_document_segments_chunks() -> None:
    fixture_dir = spec017_fixture_dir()
    policy = load_policy(load_config(None).profile())
    result = parse_file(fixture_dir / "sample.docx", policy, null_parse_options())
    assert result.status == "ok"
    assert isinstance(result.metadata, dict)
    metadata = result.metadata or {}
    assert isinstance(metadata.get("document"), dict)
    assert isinstance(metadata.get("segments"), list)
    assert isinstance(metadata.get("chunks"), list)
    assert len(metadata.get("segments", [])) > 0, "metadata should contain segments"
    assert len(metadata.get("chunks", [])) > 0, "metadata should contain chunks"
