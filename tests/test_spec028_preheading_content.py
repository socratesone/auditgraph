"""Spec-028 FR-016i pre-heading content topology.

Code and links encountered before the first heading (or in markdown files
with no headings) MUST have their origin edges attach to `document_anchor_id`
(the note entity) rather than to an ag:section.
"""
from __future__ import annotations

import secrets

import pytest

from auditgraph.extract.markdown import (
    DocumentsIndex,
    RULE_MENTIONS_TECHNOLOGY,
    RULE_REFERENCES,
    extract_markdown_subentities,
)
from auditgraph.utils.redaction import RedactionPolicy, Redactor


@pytest.fixture()
def redactor() -> Redactor:
    return Redactor(
        RedactionPolicy(policy_id="test", version="v1", enabled=True, detectors=()),
        b"\x00" * 32,
    )


@pytest.fixture()
def empty_index() -> DocumentsIndex:
    return DocumentsIndex(by_doc_id={}, by_source_path={})


ANCHOR_ID = "ent_document_anchor"


def _extract(text: str, redactor: Redactor, idx: DocumentsIndex):
    return extract_markdown_subentities(
        source_path="notes/demo.md",
        source_hash="a" * 64,
        document_id="doc_demo",
        document_anchor_id=ANCHOR_ID,
        markdown_text=text,
        redactor=redactor,
        documents_index=idx,
        pipeline_version="v0.1.0",
    )


def test_code_span_before_first_heading_attaches_mentions_technology_to_note(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Use `PostgreSQL` for storage.\n\n# First Heading\n"
    _, links = _extract(text, redactor, empty_index)
    mentions = [l for l in links if l["rule_id"] == RULE_MENTIONS_TECHNOLOGY]
    assert mentions, "pre-heading code span must emit a mentions_technology link"
    # The from side is the document anchor (note entity), not a section.
    assert all(l["from_id"] == ANCHOR_ID for l in mentions)


def test_link_before_first_heading_attaches_references_to_note(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "See [docs](https://example.com) before we start.\n\n# First Heading\n"
    _, links = _extract(text, redactor, empty_index)
    refs = [l for l in links if l["rule_id"] == RULE_REFERENCES]
    assert len(refs) == 1
    assert refs[0]["from_id"] == ANCHOR_ID


def test_markdown_file_with_no_headings_still_emits_technology_and_reference_entities(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Plain paragraph using `Redis` with [docs](https://example.com).\n"
    entities, _ = _extract(text, redactor, empty_index)
    types = {e["type"] for e in entities}
    assert "ag:technology" in types
    assert "ag:reference" in types
    # No sections emitted.
    assert "ag:section" not in types


def test_no_headings_file_attaches_all_origin_edges_to_note(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Plain paragraph `Redis` and [docs](https://example.com).\n"
    _, links = _extract(text, redactor, empty_index)
    # Every mentions_technology / references link must originate at the
    # document anchor.
    relevant = [l for l in links if l["rule_id"] in (RULE_MENTIONS_TECHNOLOGY, RULE_REFERENCES)]
    assert relevant
    for link in relevant:
        assert link["from_id"] == ANCHOR_ID


def test_pre_heading_technology_has_deterministic_id_across_runs(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Use `PostgreSQL` first.\n\n# Heading\n"
    entities_a, _ = _extract(text, redactor, empty_index)
    entities_b, _ = _extract(text, redactor, empty_index)
    techs_a = [e for e in entities_a if e["type"] == "ag:technology"]
    techs_b = [e for e in entities_b if e["type"] == "ag:technology"]
    assert [t["id"] for t in techs_a] == [t["id"] for t in techs_b]
