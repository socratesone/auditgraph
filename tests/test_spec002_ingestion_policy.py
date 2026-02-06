from __future__ import annotations

from pathlib import Path

from auditgraph.ingest.frontmatter import extract_frontmatter
from auditgraph.ingest.importer import collect_import_paths
from auditgraph.ingest.parsers import parse_file
from auditgraph.ingest.policy import SKIP_REASON_UNSUPPORTED, is_allowed, load_policy
from auditgraph.ingest.scanner import discover_files


def test_allowlist_allows_markdown_and_skips_pdf(tmp_path: Path) -> None:
    md_path = tmp_path / "notes" / "note.md"
    md_path.parent.mkdir()
    md_path.write_text("# Note", encoding="utf-8")
    pdf_path = tmp_path / "notes" / "file.pdf"
    pdf_path.write_text("%PDF", encoding="utf-8")
    py_path = tmp_path / "repos" / "app.py"
    py_path.parent.mkdir()
    py_path.write_text("print('hi')", encoding="utf-8")

    policy = load_policy({})

    assert is_allowed(md_path, policy)
    assert is_allowed(py_path, policy)
    assert not is_allowed(pdf_path, policy)

    result = parse_file(pdf_path, policy)
    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_UNSUPPORTED


def test_discover_files_sorted(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "b.txt").write_text("b", encoding="utf-8")
    (notes_dir / "a.txt").write_text("a", encoding="utf-8")

    files = discover_files(tmp_path, ["notes"], [])

    assert [path.name for path in files] == ["a.txt", "b.txt"]


def test_collect_import_paths_sorted(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "b.txt").write_text("b", encoding="utf-8")
    (notes_dir / "a.txt").write_text("a", encoding="utf-8")

    files = collect_import_paths(tmp_path, ["notes"])

    assert [path.name for path in files] == ["a.txt", "b.txt"]


def test_frontmatter_extracts_schema() -> None:
    text = """---
title: Test Note
tags: [one, two]
project: demo
status: draft
---
Body text.
"""
    payload = extract_frontmatter(text)

    assert payload["title"] == "Test Note"
    assert payload["tags"] == ["one", "two"]
    assert payload["project"] == "demo"
    assert payload["status"] == "draft"
