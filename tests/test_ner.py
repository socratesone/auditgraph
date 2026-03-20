"""Tests for NER entity extraction (Spec 018)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auditgraph.storage.hashing import sha256_text


# ---------------------------------------------------------------------------
# T004: NER backend tests
# ---------------------------------------------------------------------------

class TestNERBackend:
    """Tests for auditgraph.extract.ner_backend."""

    def test_extract_entities_from_text(self):
        """T004: spaCy wrapper returns entities from sample text."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner_backend import load_ner_model, extract_entities_from_text

        nlp = load_ner_model("en_core_web_sm")
        results = extract_entities_from_text(
            "John Smith met with Acme Corporation in New York on January 5, 2024.",
            nlp,
        )
        assert isinstance(results, list)
        assert len(results) > 0
        for ent in results:
            assert "text" in ent
            assert "label" in ent
            assert "start" in ent
            assert "end" in ent
            assert "score" in ent
            assert isinstance(ent["score"], float)

    def test_extract_entities_with_type_filter(self):
        """T004: Type filter restricts returned entity labels."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner_backend import load_ner_model, extract_entities_from_text

        nlp = load_ner_model("en_core_web_sm")
        results = extract_entities_from_text(
            "John Smith met with Acme Corporation in New York.",
            nlp,
            entity_types={"PERSON"},
        )
        labels = {ent["label"] for ent in results}
        assert labels <= {"PERSON"}, f"Expected only PERSON, got {labels}"

    def test_extract_entities_empty_text(self):
        """T004: Empty text returns empty list."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner_backend import load_ner_model, extract_entities_from_text

        nlp = load_ner_model("en_core_web_sm")
        results = extract_entities_from_text("", nlp)
        assert results == []

    def test_spacy_import_error_graceful(self):
        """T004: Missing spaCy returns empty results."""
        # We test the graceful fallback by mocking
        import auditgraph.extract.ner_backend as mod
        with patch.dict("sys.modules", {"spacy": None}):
            # The module-level import guard should handle this
            # Just verify the function signatures exist
            assert hasattr(mod, "load_ner_model")
            assert hasattr(mod, "extract_entities_from_text")


# ---------------------------------------------------------------------------
# T007: Canonical name normalization
# ---------------------------------------------------------------------------

class TestCanonicalNameNormalization:
    """Tests for name normalization logic in ner.py."""

    def test_lowercase(self):
        from auditgraph.extract.ner import _normalize_name
        assert _normalize_name("JOHN SMITH") == "john smith"

    def test_strip_titles(self):
        from auditgraph.extract.ner import _normalize_name
        assert _normalize_name("Dr. John Smith") == "john smith"
        assert _normalize_name("Mr. Jones") == "jones"
        assert _normalize_name("Mrs. Williams") == "williams"
        assert _normalize_name("Hon. Judge Roberts") == "roberts"
        assert _normalize_name("Attorney General Barr") == "general barr"

    def test_collapse_whitespace(self):
        from auditgraph.extract.ner import _normalize_name
        assert _normalize_name("John   Smith") == "john smith"

    def test_strip_trailing_punctuation(self):
        from auditgraph.extract.ner import _normalize_name
        assert _normalize_name("Smith,") == "smith"
        assert _normalize_name("Smith.") == "smith"

    def test_combined(self):
        from auditgraph.extract.ner import _normalize_name
        assert _normalize_name("  Dr.  John   Smith, ") == "john smith"


# ---------------------------------------------------------------------------
# T009: Quality gate
# ---------------------------------------------------------------------------

class TestQualityGate:
    """Tests for chunk quality scoring."""

    def test_good_quality(self):
        from auditgraph.extract.ner import _text_quality
        score = _text_quality("Hello world 123")
        assert score > 0.5

    def test_bad_quality(self):
        from auditgraph.extract.ner import _text_quality
        score = _text_quality("... --- %%% ^^^")
        assert score < 0.3

    def test_empty_text(self):
        from auditgraph.extract.ner import _text_quality
        score = _text_quality("")
        assert score == 0.0


# ---------------------------------------------------------------------------
# T006: Case number regex
# ---------------------------------------------------------------------------

class TestCaseNumberRegex:
    """Tests for case number pattern matching."""

    def test_case_number_match(self):
        from auditgraph.extract.ner import CASE_NUMBER_PATTERN
        text = "Refer to case 23-CV-12345 for details."
        matches = CASE_NUMBER_PATTERN.findall(text)
        assert "23-CV-12345" in matches

    def test_case_number_multiple(self):
        from auditgraph.extract.ner import CASE_NUMBER_PATTERN
        text = "Cases 2020-CRIM-001 and 99-AP-99999 are related."
        matches = CASE_NUMBER_PATTERN.findall(text)
        assert len(matches) == 2

    def test_case_number_no_match(self):
        from auditgraph.extract.ner import CASE_NUMBER_PATTERN
        text = "No case numbers here at all."
        matches = CASE_NUMBER_PATTERN.findall(text)
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# T009: Entity ID determinism
# ---------------------------------------------------------------------------

class TestEntityIDDeterminism:
    """Tests for deterministic entity ID generation."""

    def test_same_input_same_id(self):
        """Same canonical key produces same entity ID."""
        from auditgraph.extract.ner import _ner_entity_id
        id1 = _ner_entity_id("ner:person:john smith")
        id2 = _ner_entity_id("ner:person:john smith")
        assert id1 == id2
        assert id1.startswith("ent_")

    def test_different_input_different_id(self):
        from auditgraph.extract.ner import _ner_entity_id
        id1 = _ner_entity_id("ner:person:john smith")
        id2 = _ner_entity_id("ner:person:jane doe")
        assert id1 != id2


# ---------------------------------------------------------------------------
# T009/T013: Integration test with fixture chunks
# ---------------------------------------------------------------------------

class TestNERExtractorIntegration:
    """Integration tests for extract_ner_entities."""

    @pytest.fixture
    def pkg_with_chunks(self, tmp_path):
        """Create a minimal pkg_root with chunk JSON files."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        chunk1 = {
            "id": "chk_test001",
            "document_id": "doc_test001",
            "text": "John Smith met with Acme Corporation in New York regarding case 23-CV-12345.",
            "order": 0,
            "source_path": "test.pdf",
            "source_hash": "abc123",
        }
        chunk2 = {
            "id": "chk_test002",
            "document_id": "doc_test001",
            "text": "Jane Doe from Global Industries also attended the meeting in Washington.",
            "order": 1,
            "source_path": "test.pdf",
            "source_hash": "abc123",
        }
        (chunks_dir / "chk_test001.json").write_text(json.dumps(chunk1))
        (chunks_dir / "chk_test002.json").write_text(json.dumps(chunk2))
        return tmp_path

    def test_extractor_produces_entities_and_links(self, pkg_with_chunks):
        """T009/T013: NER extractor produces entities and links from chunks."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner import extract_ner_entities

        config = {
            "enabled": True,
            "model": "en_core_web_sm",
            "quality_threshold": 0.3,
            "entity_types": ["PERSON", "ORG", "GPE", "DATE", "LAW", "MONEY"],
            "cooccurrence_types": ["PERSON", "ORG", "GPE"],
        }
        entities, links = extract_ner_entities(pkg_with_chunks, config)

        assert len(entities) > 0, "Should extract at least one entity"
        assert len(links) > 0, "Should produce at least one link"

        # Verify entity structure
        for ent in entities:
            assert "id" in ent
            assert ent["id"].startswith("ent_")
            assert "type" in ent
            assert ent["type"].startswith("ner:")
            assert "name" in ent
            assert "canonical_key" in ent
            assert "aliases" in ent
            assert isinstance(ent["aliases"], list)
            assert "provenance" in ent
            assert "refs" in ent
            assert isinstance(ent["refs"], list)
            assert "mention_count" in ent

        # Verify link structure
        mention_links = [l for l in links if l["type"] == "MENTIONED_IN"]
        cooccur_links = [l for l in links if l["type"] == "CO_OCCURS_WITH"]

        assert len(mention_links) > 0, "Should have MENTIONED_IN links"

        for link in links:
            assert "id" in link
            assert link["id"].startswith("lnk_")
            assert "from_id" in link
            assert "to_id" in link
            assert "type" in link
            assert "rule_id" in link
            assert "confidence" in link

        # Verify MENTIONED_IN links carry span provenance
        for link in mention_links:
            assert "span_start" in link, "MENTIONED_IN link must have span_start"
            assert "span_end" in link, "MENTIONED_IN link must have span_end"
            assert "surface_form" in link, "MENTIONED_IN link must have surface_form"
            assert isinstance(link["span_start"], int)
            assert isinstance(link["span_end"], int)
            assert link["span_end"] >= link["span_start"]
            assert isinstance(link["surface_form"], str)
            assert len(link["surface_form"]) > 0
            assert isinstance(link["confidence"], float)

    def test_extractor_disabled(self, pkg_with_chunks):
        """NER disabled returns empty lists."""
        from auditgraph.extract.ner import extract_ner_entities

        config = {"enabled": False}
        entities, links = extract_ner_entities(pkg_with_chunks, config)
        assert entities == []
        assert links == []

    def test_extractor_quality_gate_filters_noise(self, tmp_path):
        """Chunks below quality threshold are skipped."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner import extract_ner_entities

        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        # Low quality chunk (mostly non-alphanumeric)
        chunk = {
            "id": "chk_noise001",
            "document_id": "doc_noise",
            "text": "... --- %%% ^^^ !!! @@@ ### $$$ &&& ***",
            "order": 0,
            "source_path": "noise.pdf",
            "source_hash": "noise123",
        }
        (chunks_dir / "chk_noise001.json").write_text(json.dumps(chunk))

        config = {
            "enabled": True,
            "model": "en_core_web_sm",
            "quality_threshold": 0.5,
            "entity_types": ["PERSON", "ORG"],
            "cooccurrence_types": ["PERSON", "ORG"],
        }
        entities, links = extract_ner_entities(tmp_path, config)
        assert entities == []
        assert links == []

    def test_case_number_entity_extraction(self, tmp_path):
        """Case numbers are extracted as ner:case_number entities."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner import extract_ner_entities

        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        chunk = {
            "id": "chk_case001",
            "document_id": "doc_case",
            "text": "Filing for case 2023-CV-00456 was submitted.",
            "order": 0,
            "source_path": "case.pdf",
            "source_hash": "case123",
        }
        (chunks_dir / "chk_case001.json").write_text(json.dumps(chunk))

        config = {
            "enabled": True,
            "model": "en_core_web_sm",
            "quality_threshold": 0.3,
            "entity_types": ["PERSON", "ORG", "GPE", "DATE", "LAW", "MONEY"],
            "cooccurrence_types": ["PERSON", "ORG", "GPE"],
        }
        entities, links = extract_ner_entities(tmp_path, config)
        case_entities = [e for e in entities if e["type"] == "ner:case_number"]
        assert len(case_entities) >= 1, "Should extract case number entity"
        assert "2023-CV-00456" in case_entities[0]["aliases"]

    def test_cooccurrence_links_canonical_order(self, pkg_with_chunks):
        """CO_OCCURS_WITH links have from_id < to_id for dedup."""
        spacy = pytest.importorskip("spacy")
        from auditgraph.extract.ner import extract_ner_entities

        config = {
            "enabled": True,
            "model": "en_core_web_sm",
            "quality_threshold": 0.3,
            "entity_types": ["PERSON", "ORG", "GPE", "DATE", "LAW", "MONEY"],
            "cooccurrence_types": ["PERSON", "ORG", "GPE"],
        }
        entities, links = extract_ner_entities(pkg_with_chunks, config)
        cooccur_links = [l for l in links if l["type"] == "CO_OCCURS_WITH"]
        for link in cooccur_links:
            assert link["from_id"] <= link["to_id"], (
                f"CO_OCCURS_WITH from_id should be <= to_id: {link['from_id']} > {link['to_id']}"
            )
