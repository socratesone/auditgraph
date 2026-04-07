"""Tests for the opt-in code-chunking feature.

By default, source code files (.py, .js, .ts, .tsx, .jsx) are routed to
parser_id == "text/code" in `auditgraph/ingest/policy.py` but are NOT
passed through `_build_document_metadata`, so they produce zero chunks.
Code becomes `file` entities only via `extract.code_symbols.v1`, with no
searchable body content.

This module verifies that setting
`profiles.<name>.ingestion.chunk_code.enabled: true` opts code files into
the same sliding-window chunker that text/markdown and text/plain use,
making code body content BM25-searchable. With the flag off (default),
code files produce zero chunks (current behavior).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root


def _write_test_workspace(tmp_path: Path, chunk_code_enabled: bool) -> tuple[PipelineRunner, object, Path]:
    """Create a workspace with one .py file and one .md file, run ingest."""
    notes = tmp_path / "notes"
    notes.mkdir()

    # Markdown file (control: should always produce chunks)
    (notes / "intro.md").write_text(
        "# Introduction\n\nThis is the intro to the project. It explains "
        "what the project is and why it exists.\n"
    )

    # Python file (variable: should produce chunks only when flag is on)
    (notes / "module.py").write_text(
        '"""A small module for testing."""\n'
        "def greet(name):\n"
        '    """Return a greeting for the given name."""\n'
        '    return f"Hello, {name}!"\n'
        "\n"
        "def farewell(name):\n"
        '    """Return a farewell for the given name."""\n'
        '    return f"Goodbye, {name}!"\n'
    )

    chunk_code_yaml = "true" if chunk_code_enabled else "false"
    cfg_path = tmp_path / "test_config.yaml"
    cfg_path.write_text(
        "pkg_root: '.'\n"
        "active_profile: 'default'\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: ['notes']\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: ['.md', '.py']\n"
        "      ocr_mode: 'off'\n"
        "      chunk_tokens: 200\n"
        "      chunk_overlap_tokens: 40\n"
        "      max_file_size_bytes: 10000000\n"
        f"      chunk_code:\n"
        f"        enabled: {chunk_code_yaml}\n"
        "    extraction:\n"
        "      ner:\n"
        "        enabled: false\n"
    )

    config = load_config(cfg_path)
    runner = PipelineRunner()
    result = runner.run_ingest(root=tmp_path, config=config)
    assert result.status == "ok", f"ingest failed: {result.detail}"

    return runner, config, tmp_path


def _count_chunks_for_extension(pkg_root: Path, ext: str) -> int:
    """Count chunks whose source_path ends with the given extension."""
    import json
    chunks_dir = pkg_root / "chunks"
    if not chunks_dir.exists():
        return 0
    count = 0
    for path in chunks_dir.rglob("*.json"):
        try:
            chunk = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        src = chunk.get("source_path", "")
        if src.lower().endswith(ext.lower()):
            count += 1
    return count


class TestCodeChunkingDisabledByDefault:
    """Default behavior: code files produce 0 chunks; markdown produces > 0."""

    def test_markdown_produces_chunks(self, tmp_path):
        runner, config, root = _write_test_workspace(tmp_path, chunk_code_enabled=False)
        pkg_root = profile_pkg_root(root, config)
        md_chunks = _count_chunks_for_extension(pkg_root, ".md")
        assert md_chunks > 0, "Expected the .md file to produce at least one chunk"

    def test_python_produces_no_chunks_when_flag_off(self, tmp_path):
        runner, config, root = _write_test_workspace(tmp_path, chunk_code_enabled=False)
        pkg_root = profile_pkg_root(root, config)
        py_chunks = _count_chunks_for_extension(pkg_root, ".py")
        assert py_chunks == 0, (
            f"Expected 0 chunks for .py files when chunk_code.enabled=false; "
            f"found {py_chunks}"
        )


class TestCodeChunkingOptIn:
    """When chunk_code.enabled=true, code files produce chunks too."""

    def test_python_produces_chunks_when_flag_on(self, tmp_path):
        runner, config, root = _write_test_workspace(tmp_path, chunk_code_enabled=True)
        pkg_root = profile_pkg_root(root, config)
        py_chunks = _count_chunks_for_extension(pkg_root, ".py")
        assert py_chunks > 0, (
            f"Expected at least one chunk for the .py file when "
            f"chunk_code.enabled=true; found {py_chunks}"
        )

    def test_markdown_still_chunks_when_code_chunking_enabled(self, tmp_path):
        """Enabling code chunking must not break markdown chunking."""
        runner, config, root = _write_test_workspace(tmp_path, chunk_code_enabled=True)
        pkg_root = profile_pkg_root(root, config)
        md_chunks = _count_chunks_for_extension(pkg_root, ".md")
        assert md_chunks > 0, (
            "Expected the .md file to still produce chunks when chunk_code.enabled=true"
        )

    def test_python_chunks_contain_function_body_text(self, tmp_path):
        """The produced code chunks should contain the actual source text
        (so BM25 search can find content within the file)."""
        import json
        runner, config, root = _write_test_workspace(tmp_path, chunk_code_enabled=True)
        pkg_root = profile_pkg_root(root, config)
        chunks_dir = pkg_root / "chunks"
        all_text = ""
        for path in chunks_dir.rglob("*.json"):
            chunk = json.loads(path.read_text())
            src = chunk.get("source_path", "")
            if src.lower().endswith(".py"):
                all_text += chunk.get("text", "")
        # Both function names from our test fixture should appear somewhere
        # in the chunked content
        assert "greet" in all_text, (
            "Expected 'greet' function name in code chunks; not found"
        )
        assert "farewell" in all_text, (
            "Expected 'farewell' function name in code chunks; not found"
        )
