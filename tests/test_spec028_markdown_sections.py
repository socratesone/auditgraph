"""Spec-028 US2 · `ag:section` emission tests.

Exercises FR-006/FR-007/FR-016i (heading-parent rule), invariant I5
(no dangling parents), and ID determinism for sections.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from auditgraph.extract.markdown import DocumentsIndex, extract_markdown_subentities
from auditgraph.utils.redaction import RedactionPolicy, Redactor

FIXTURES = Path(__file__).parent / "fixtures" / "spec028"


@pytest.fixture()
def redactor() -> Redactor:
    return Redactor(
        RedactionPolicy(policy_id="test", version="v1", enabled=True, detectors=()),
        secrets.token_bytes(32),
    )


@pytest.fixture()
def empty_index() -> DocumentsIndex:
    return DocumentsIndex(by_doc_id={}, by_source_path={})


def _extract(text: str, redactor: Redactor, idx: DocumentsIndex, *, source_hash: str = "a" * 64) -> tuple[list, list]:
    return extract_markdown_subentities(
        source_path="notes/demo.md",
        source_hash=source_hash,
        document_id="doc_test",
        document_anchor_id="ent_anchor",
        markdown_text=text,
        redactor=redactor,
        documents_index=idx,
        pipeline_version="v0.1.0",
    )


def _sections(entities: list) -> list[dict]:
    return [e for e in entities if e["type"] == "ag:section"]


def test_single_h1_emits_one_section(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    entities, _ = _extract("# Introduction\n\nhello\n", redactor, empty_index)
    sections = _sections(entities)
    assert len(sections) == 1
    assert sections[0]["name"] == "Introduction"
    assert sections[0]["level"] == 1
    assert sections[0]["parent_section_id"] is None


def test_nested_headings_build_parent_chain(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = (FIXTURES / "nested_headings.md").read_text()
    entities, _ = _extract(text, redactor, empty_index)
    sections = {s["name"]: s for s in _sections(entities)}
    # H1 "Introduction" → parent None
    intro = sections["Introduction"]
    assert intro["parent_section_id"] is None
    # H2 "Install" → parent Introduction
    install = sections["Install"]
    assert install["parent_section_id"] == intro["id"]
    # H3 "Prerequisites" → parent Install
    prereq = sections["Prerequisites"]
    assert prereq["parent_section_id"] == install["id"]
    # H2 "Configuration" → parent Introduction (Install H2 popped)
    config = sections["Configuration"]
    assert config["parent_section_id"] == intro["id"]
    # H1 "Appendix" → parent None (everything popped)
    appendix = sections["Appendix"]
    assert appendix["parent_section_id"] is None


def test_setext_headings_are_captured(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = (FIXTURES / "nested_headings.md").read_text()
    entities, _ = _extract(text, redactor, empty_index)
    names = {s["name"] for s in _sections(entities)}
    assert "Setext Heading One" in names
    assert "Setext Heading Two" in names


def test_section_name_is_redacted(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    """Heading text passes through the Redactor (defense-in-depth)."""
    text = (FIXTURES / "with_secrets.md").read_text()
    # The null-detector redactor returns content as-is — but the call site
    # still invokes the Redactor. Use a detector-equipped redactor to test
    # that secrets get scrubbed.
    from auditgraph.utils.redaction import RedactionPolicy, _default_detectors
    from auditgraph.utils.redaction import Redactor as R

    registry = _default_detectors()
    detector_policy = RedactionPolicy(
        policy_id="test.jwt",
        version="v1",
        enabled=True,
        detectors=(registry["jwt"],),
    )
    strict_redactor = R(detector_policy, secrets.token_bytes(32))
    entities2, _ = extract_markdown_subentities(
        source_path="notes/demo.md",
        source_hash="a" * 64,
        document_id="doc_test",
        document_anchor_id="ent_anchor",
        markdown_text=text,
        redactor=strict_redactor,
        documents_index=empty_index,
        pipeline_version="v0.1.0",
    )
    strict_sections = [e for e in entities2 if e["type"] == "ag:section"]
    # Heading that contained a JWT must no longer contain the raw token.
    offending = [
        s
        for s in strict_sections
        if "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123XYZ" in s["name"]
    ]
    assert not offending, (
        f"section name leaked a JWT past redaction: {offending}"
    )


def test_section_order_is_zero_based_and_increments(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = "# A\n## B\n# C\n"
    entities, _ = _extract(text, redactor, empty_index)
    sections = _sections(entities)
    orders = {s["name"]: s["order"] for s in sections}
    assert orders["A"] == 0
    assert orders["B"] == 1
    assert orders["C"] == 2


def test_sections_invariant_i5_no_dangling_parents(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = (FIXTURES / "nested_headings.md").read_text()
    entities, _ = _extract(text, redactor, empty_index)
    sections = _sections(entities)
    section_ids = {s["id"] for s in sections}
    for s in sections:
        parent = s.get("parent_section_id")
        assert parent is None or parent in section_ids, (
            f"dangling parent: section {s['name']!r} points at {parent!r} which isn't in the emitted set"
        )


def test_section_id_is_source_hash_scoped(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    """Same heading text in two different documents MUST produce distinct section IDs."""
    text = "# Introduction\n\nhello\n"
    entities_a, _ = _extract(text, redactor, empty_index, source_hash="a" * 64)
    entities_b, _ = _extract(text, redactor, empty_index, source_hash="b" * 64)
    section_a = next(e for e in entities_a if e["type"] == "ag:section")
    section_b = next(e for e in entities_b if e["type"] == "ag:section")
    assert section_a["id"] != section_b["id"], (
        "source_hash MUST be part of the ID input — otherwise two docs with "
        "identical headings collide"
    )
    # But canonical_key (human-readable) SHOULD match because the slug is the same.
    assert section_a["canonical_key"] == section_b["canonical_key"]
