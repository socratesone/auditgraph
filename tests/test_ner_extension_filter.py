"""Tests for the NER natural-language extension filter.

When a chunk's source file is not natural-language content (e.g., code),
the NER extractor MUST skip it instead of running expensive spaCy inference
that produces mostly false-positive entities from variable and function names.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auditgraph.extract.ner import extract_ner_entities


def _write_chunk(chunks_dir: Path, chunk_id: str, source_path: str, text: str) -> None:
    """Write a chunk JSON file with the given source_path and text."""
    chunk = {
        "id": chunk_id,
        "chunk_id": chunk_id,
        "document_id": "doc_test",
        "text": text,
        "order": 0,
        "source_path": source_path,
        "source_hash": "abc123",
    }
    (chunks_dir / f"{chunk_id}.json").write_text(json.dumps(chunk))


def _make_mock_nlp(call_log: list[str]) -> MagicMock:
    """Make a mock spaCy nlp object that records every text it was called with.

    Returns a mock whose `__call__` appends the text to call_log and returns
    a Doc-like object with a single PERSON entity at offsets 0..10.
    """
    fake_ent = MagicMock()
    fake_ent.text = "Mock Person"
    fake_ent.label_ = "PERSON"
    fake_ent.start_char = 0
    fake_ent.end_char = 10

    fake_doc = MagicMock()
    fake_doc.ents = [fake_ent]

    def _call(text):
        call_log.append(text)
        return fake_doc

    nlp = MagicMock(side_effect=_call)
    return nlp


@pytest.fixture
def pkg_with_mixed_chunks(tmp_path):
    """Workspace containing one .md chunk, one .py chunk, and one .pdf chunk."""
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunk(
        chunks_dir,
        "chk_md001",
        "/abs/path/notes.md",
        "John Smith met with Acme Corporation in New York yesterday.",
    )
    _write_chunk(
        chunks_dir,
        "chk_py001",
        "/abs/path/auditgraph/cli.py",
        "def main(): parser = argparse.ArgumentParser(); return parser.parse_args()",
    )
    _write_chunk(
        chunks_dir,
        "chk_pdf001",
        "/abs/path/contracts/nda.pdf",
        "Jane Doe signed the agreement with Global Industries on January 5, 2024.",
    )
    return tmp_path


class TestNaturalLanguageExtensionFilter:
    """Verify NER skips chunks whose source file is not natural-language content."""

    def test_md_chunk_is_processed(self, pkg_with_mixed_chunks, monkeypatch):
        """A chunk from a .md file should be passed through to spaCy."""
        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(pkg_with_mixed_chunks, config)

        md_calls = [t for t in call_log if "John Smith" in t]
        assert len(md_calls) == 1, (
            f"Expected the .md chunk to be processed exactly once; "
            f"got {len(md_calls)} calls. All calls: {call_log}"
        )

    def test_pdf_chunk_is_processed(self, pkg_with_mixed_chunks, monkeypatch):
        """A chunk from a .pdf file should be passed through to spaCy."""
        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(pkg_with_mixed_chunks, config)

        pdf_calls = [t for t in call_log if "Jane Doe" in t]
        assert len(pdf_calls) == 1, (
            f"Expected the .pdf chunk to be processed exactly once; "
            f"got {len(pdf_calls)} calls. All calls: {call_log}"
        )

    def test_py_chunk_is_skipped_by_default(self, pkg_with_mixed_chunks, monkeypatch):
        """A chunk from a .py file should NOT be passed to spaCy by default."""
        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(pkg_with_mixed_chunks, config)

        py_calls = [t for t in call_log if "argparse" in t]
        assert len(py_calls) == 0, (
            f"Expected the .py chunk to be skipped; got {len(py_calls)} calls. "
            f"All calls: {call_log}"
        )

    def test_only_md_and_pdf_processed_by_default(self, pkg_with_mixed_chunks, monkeypatch):
        """End-to-end: with three mixed chunks, only the two NL ones reach spaCy."""
        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(pkg_with_mixed_chunks, config)

        assert len(call_log) == 2, (
            f"Expected exactly 2 spaCy calls (md + pdf), got {len(call_log)}: {call_log}"
        )

    def test_user_can_opt_in_code_via_config(self, pkg_with_mixed_chunks, monkeypatch):
        """Setting natural_language_extensions to include .py overrides the default."""
        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
            "natural_language_extensions": [".md", ".pdf", ".py"],
        }
        extract_ner_entities(pkg_with_mixed_chunks, config)

        py_calls = [t for t in call_log if "argparse" in t]
        assert len(py_calls) == 1, (
            f"Expected the .py chunk to be processed when explicitly allowlisted; "
            f"got {len(py_calls)} calls. All calls: {call_log}"
        )

    def test_extensionless_file_is_skipped(self, tmp_path, monkeypatch):
        """A chunk from a file with no extension (e.g., Makefile) should be skipped."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        _write_chunk(
            chunks_dir,
            "chk_make",
            "/abs/path/Makefile",
            "John Smith owns the build pipeline.",
        )

        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(tmp_path, config)

        assert len(call_log) == 0, (
            f"Expected the extensionless Makefile chunk to be skipped; "
            f"got {len(call_log)} calls."
        )

    def test_uppercase_extension_is_normalized(self, tmp_path, monkeypatch):
        """A chunk from a .MD (uppercase) file should be processed (case-insensitive)."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        _write_chunk(
            chunks_dir,
            "chk_upper",
            "/abs/path/README.MD",
            "John Smith works at Acme Corporation.",
        )

        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(tmp_path, config)

        assert len(call_log) == 1, (
            f"Expected uppercase .MD to be normalized and processed; "
            f"got {len(call_log)} calls."
        )

    def test_chunk_without_source_path_is_processed(self, tmp_path, monkeypatch):
        """A chunk with missing/empty source_path should be processed (safe default).

        Legacy chunks may not have source_path set; we should not silently drop them.
        """
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        chunk = {
            "id": "chk_legacy",
            "chunk_id": "chk_legacy",
            "document_id": "doc_test",
            "text": "John Smith met Jane Doe in New York.",
            "order": 0,
            # NOTE: no source_path
            "source_hash": "abc123",
        }
        (chunks_dir / "chk_legacy.json").write_text(json.dumps(chunk))

        call_log: list[str] = []
        nlp = _make_mock_nlp(call_log)
        monkeypatch.setattr(
            "auditgraph.extract.ner_backend.load_ner_model",
            lambda model_name: nlp,
        )

        config = {
            "enabled": True,
            "model": "mock_model",
            "quality_threshold": 0.0,
            "entity_types": ["PERSON"],
            "cooccurrence_types": [],
        }
        extract_ner_entities(tmp_path, config)

        assert len(call_log) == 1, (
            f"Expected legacy chunk without source_path to be processed; "
            f"got {len(call_log)} calls."
        )
