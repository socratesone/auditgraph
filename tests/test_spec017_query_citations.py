from __future__ import annotations

import shutil

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.keyword import keyword_search
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.loaders import load_chunks
from tests.support import spec017_fixture_dir


def _prepare_workspace(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = spec017_fixture_dir()
    for name in ("sample.pdf", "sample.docx"):
        shutil.copy2(fixture_dir / name, docs_dir / name)
    return docs_dir


def test_spec017_chunk_citation_metadata_presence(tmp_path):
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    pkg_root = profile_pkg_root(tmp_path, config)
    results = keyword_search(pkg_root, "sample")
    chunk_results = [result for result in results if str(result.get("id", "")).startswith("chk_")]
    assert chunk_results
    citation = chunk_results[0].get("citation", {})
    assert isinstance(citation, dict)
    assert citation.get("source_path")


def test_spec017_no_inline_citation_markers(tmp_path):
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir)])

    pkg_root = profile_pkg_root(tmp_path, config)
    chunks = load_chunks(pkg_root)
    assert chunks
    assert all("[[page:" not in str(chunk.get("text", "")) for chunk in chunks)


def test_spec017_docx_paragraph_order_provenance(tmp_path):
    docs_dir = _prepare_workspace(tmp_path)
    config = load_config(None)
    runner = PipelineRunner()
    runner.run_import(root=tmp_path, config=config, targets=[str(docs_dir / "sample.docx")])

    pkg_root = profile_pkg_root(tmp_path, config)
    chunks = load_chunks(pkg_root)
    docx_chunks = [chunk for chunk in chunks if str(chunk.get("source_path", "")).endswith("sample.docx")]
    assert docx_chunks
    assert all(chunk.get("paragraph_index_start") is not None for chunk in docx_chunks)
    def _order(chunk: dict[str, object]) -> int:
        value = chunk.get("order", 0)
        return value if isinstance(value, int) else 0

    ordered = sorted(docx_chunks, key=_order)
    assert ordered == docx_chunks
