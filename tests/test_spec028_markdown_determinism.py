"""Spec-028 US2 · Determinism invariant I1.

Two runs of extract_markdown_subentities with identical inputs MUST
produce byte-identical (entities, links) lists — same order, same
content, same IDs.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.extract.markdown import DocumentsIndex, extract_markdown_subentities
from auditgraph.utils.redaction import RedactionPolicy, Redactor

FIXTURES = Path(__file__).parent / "fixtures" / "spec028"


@pytest.fixture()
def redactor() -> Redactor:
    # Note: use a FIXED key for determinism. Random-keyed redactors would
    # rotate tokens between calls, breaking determinism for any secret-
    # containing text. Tests using secret fixtures need an idempotent
    # setup; for this test we use a non-secret fixture so the key is
    # immaterial.
    return Redactor(
        RedactionPolicy(policy_id="test", version="v1", enabled=True, detectors=()),
        b"\x00" * 32,
    )


@pytest.fixture()
def empty_index() -> DocumentsIndex:
    return DocumentsIndex(by_doc_id={}, by_source_path={})


def _extract(text: str, redactor: Redactor, idx: DocumentsIndex) -> tuple[list, list]:
    return extract_markdown_subentities(
        source_path="notes/demo.md",
        source_hash="a" * 64,
        document_id="doc_test",
        document_anchor_id="ent_anchor",
        markdown_text=text,
        redactor=redactor,
        documents_index=idx,
        pipeline_version="v0.1.0",
    )


def test_two_runs_produce_identical_entity_ids(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = (FIXTURES / "code_and_links.md").read_text()
    entities_a, _ = _extract(text, redactor, empty_index)
    entities_b, _ = _extract(text, redactor, empty_index)
    ids_a = [e["id"] for e in entities_a]
    ids_b = [e["id"] for e in entities_b]
    assert ids_a == ids_b, "entity IDs drifted across runs on identical input"


def test_two_runs_produce_identical_link_ids(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = (FIXTURES / "code_and_links.md").read_text()
    _, links_a = _extract(text, redactor, empty_index)
    _, links_b = _extract(text, redactor, empty_index)
    assert [link["id"] for link in links_a] == [link["id"] for link in links_b]


def test_two_runs_produce_byte_identical_json_payloads(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = (FIXTURES / "nested_headings.md").read_text()
    entities_a, links_a = _extract(text, redactor, empty_index)
    entities_b, links_b = _extract(text, redactor, empty_index)
    ja = json.dumps([entities_a, links_a], sort_keys=True)
    jb = json.dumps([entities_b, links_b], sort_keys=True)
    assert ja == jb


def test_determinism_holds_on_workspace_fixture(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    """I1: even with a mixed corpus of fixtures, reruns are stable."""
    for md_path in sorted((FIXTURES / "workspace").glob("*.md")):
        text = md_path.read_text()
        a = _extract(text, redactor, empty_index)
        b = _extract(text, redactor, empty_index)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), (
            f"non-determinism in {md_path.name}"
        )
