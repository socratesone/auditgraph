"""Spec-028 US2 · `ag:reference` emission and classification tests.

Exercises FR-009/FR-010/FR-016f (resolution rules), FR-016g (image skip),
FR-016h (autolinks + bare URLs via linkify), invariant I3 (internal
targets exist), and the parallel link topology (every reference gets an
inbound `references` edge; only internal references get an outbound
`resolves_to_document` edge).
"""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from auditgraph.extract.markdown import (
    RULE_REFERENCES,
    RULE_RESOLVES_TO_DOCUMENT,
    DocumentsIndex,
    extract_markdown_subentities,
)
from auditgraph.utils.redaction import RedactionPolicy, Redactor

FIXTURES = Path(__file__).parent / "fixtures" / "spec028"


@pytest.fixture()
def redactor() -> Redactor:
    return Redactor(
        RedactionPolicy(policy_id="test", version="v1", enabled=True, detectors=()),
        secrets.token_bytes(32),
    )


def _extract(
    text: str,
    redactor: Redactor,
    idx: DocumentsIndex,
    *,
    source_path: str = "notes/demo.md",
    source_hash: str = "a" * 64,
):
    return extract_markdown_subentities(
        source_path=source_path,
        source_hash=source_hash,
        document_id="doc_test",
        document_anchor_id="ent_anchor",
        markdown_text=text,
        redactor=redactor,
        documents_index=idx,
        pipeline_version="v0.1.0",
    )


def _refs(entities: list) -> list[dict]:
    return [e for e in entities if e["type"] == "ag:reference"]


def test_internal_reference_resolves_to_document_id(redactor: Redactor) -> None:
    idx = DocumentsIndex(
        by_doc_id={"doc_setup": Path("/fake/doc_setup.json")},
        by_source_path={"notes/setup.md": "doc_setup"},
    )
    entities, _ = _extract(
        "See [setup](setup.md).\n",
        redactor,
        idx,
        source_path="notes/intro.md",
    )
    refs = _refs(entities)
    assert len(refs) == 1
    assert refs[0]["resolution"] == "internal"
    assert refs[0]["target_document_id"] == "doc_setup"


def test_external_reference_classified_by_scheme(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("See [docs](https://example.com).\n", redactor, idx)
    refs = _refs(entities)
    assert refs[0]["resolution"] == "external"
    assert refs[0]["target_document_id"] is None


def test_autolink_classified_external(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("Visit <https://example.com>.\n", redactor, idx)
    refs = _refs(entities)
    assert len(refs) == 1
    assert refs[0]["resolution"] == "external"


def test_bare_url_in_prose_via_linkify_classified_external(redactor: Redactor) -> None:
    """FR-016h: bare URLs (no `<>`) emit an ag:reference via linkify."""
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("Or plain https://example.com/bare.\n", redactor, idx)
    refs = _refs(entities)
    assert len(refs) == 1
    assert refs[0]["resolution"] == "external"
    assert refs[0]["target"] == "https://example.com/bare"


def test_broken_relative_link_is_unresolved(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("See [ghost](does-not-exist.md).\n", redactor, idx)
    refs = _refs(entities)
    assert refs[0]["resolution"] == "unresolved"
    assert refs[0]["target_document_id"] is None


def test_fragment_only_link_is_unresolved(redactor: Redactor) -> None:
    """FR-016f: `#anchor` → unresolved (in-document anchors out of scope)."""
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("Jump to [anchor](#install).\n", redactor, idx)
    refs = _refs(entities)
    assert refs[0]["resolution"] == "unresolved"


def test_combined_path_and_fragment_classifies_on_path(redactor: Redactor) -> None:
    """FR-016f: `setup.md#install` classifies on the path portion only."""
    idx = DocumentsIndex(
        by_doc_id={"doc_setup": Path("/fake/doc_setup.json")},
        by_source_path={"notes/setup.md": "doc_setup"},
    )
    entities, _ = _extract(
        "Go to [install](setup.md#install).\n",
        redactor,
        idx,
        source_path="notes/intro.md",
    )
    refs = _refs(entities)
    assert refs[0]["resolution"] == "internal"
    assert refs[0]["target_document_id"] == "doc_setup"


def test_query_string_stripped_before_resolution(redactor: Redactor) -> None:
    idx = DocumentsIndex(
        by_doc_id={"doc_setup": Path("/fake/doc_setup.json")},
        by_source_path={"notes/setup.md": "doc_setup"},
    )
    entities, _ = _extract(
        "Go to [tabbed](setup.md?tab=install).\n",
        redactor,
        idx,
        source_path="notes/intro.md",
    )
    refs = _refs(entities)
    assert refs[0]["resolution"] == "internal"


def test_directory_or_bare_name_is_unresolved(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("See [dir](subdir/).\n", redactor, idx)
    refs = _refs(entities)
    assert refs[0]["resolution"] == "unresolved"
    # And a bare-no-extension.
    entities2, _ = _extract("See [bare](README).\n", redactor, idx)
    refs2 = _refs(entities2)
    assert refs2[0]["resolution"] == "unresolved"


def test_mailto_scheme_is_external(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("Contact [me](mailto:x@example.com).\n", redactor, idx)
    refs = _refs(entities)
    assert refs[0]["resolution"] == "external"


def test_image_emits_no_reference_and_no_technology(redactor: Redactor) -> None:
    """FR-016g v1: images are skipped entirely."""
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    entities, _ = _extract("Here: ![alt text](diagram.png)\n", redactor, idx)
    refs = _refs(entities)
    techs = [e for e in entities if e["type"] == "ag:technology"]
    assert refs == []
    assert techs == []


def test_every_reference_has_inbound_references_link(redactor: Redactor) -> None:
    idx = DocumentsIndex(by_doc_id={}, by_source_path={})
    text = "See [a](a.md), [b](b.md), and <https://example.com>.\n"
    entities, links = _extract(text, redactor, idx)
    refs = _refs(entities)
    ref_ids = {r["id"] for r in refs}
    references_link_tos = {
        link["to_id"] for link in links if link["rule_id"] == RULE_REFERENCES
    }
    assert ref_ids == references_link_tos, (
        "every ag:reference must receive exactly one `references` inbound edge"
    )


def test_only_internal_reference_has_outbound_resolves_to_document_link(
    redactor: Redactor,
) -> None:
    idx = DocumentsIndex(
        by_doc_id={"doc_x": Path("/fake/doc_x.json")},
        by_source_path={"notes/x.md": "doc_x"},
    )
    text = "Internal [x](x.md), external <https://example.com>, broken [b](nope.md).\n"
    entities, links = _extract(text, redactor, idx, source_path="notes/intro.md")
    refs = _refs(entities)
    resolves_from_ids = {
        link["from_id"] for link in links if link["rule_id"] == RULE_RESOLVES_TO_DOCUMENT
    }
    internal_ids = {r["id"] for r in refs if r["resolution"] == "internal"}
    assert resolves_from_ids == internal_ids


def test_references_invariant_i3_internal_targets_have_link(redactor: Redactor) -> None:
    idx = DocumentsIndex(
        by_doc_id={"doc_a": Path("/fake/doc_a.json"), "doc_b": Path("/fake/doc_b.json")},
        by_source_path={"notes/a.md": "doc_a", "notes/b.md": "doc_b"},
    )
    text = "[a](a.md) [b](b.md) [x](nope.md)\n"
    entities, links = _extract(text, redactor, idx, source_path="notes/intro.md")
    refs = _refs(entities)
    resolves = [link for link in links if link["rule_id"] == RULE_RESOLVES_TO_DOCUMENT]
    for ref in refs:
        if ref["resolution"] == "internal":
            matching = [link for link in resolves if link["from_id"] == ref["id"]]
            assert len(matching) == 1, (
                f"I3 violated: internal ref {ref['id']} has no resolves_to_document edge"
            )
            assert matching[0]["to_id"] == ref["target_document_id"]
