"""Spec-028 US2 · `ag:technology` emission tests.

Exercises FR-008/FR-016g (fence info-only rule), per-document dedup via
case-fold + whitespace-trim normalization, and invariant I4.
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


def _extract(text: str, redactor: Redactor, idx: DocumentsIndex, *, source_hash: str = "a" * 64):
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


def _techs(entities: list) -> list[dict]:
    return [e for e in entities if e["type"] == "ag:technology"]


def test_inline_code_emits_technology(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    entities, _ = _extract("Use `PostgreSQL` for storage.\n", redactor, empty_index)
    techs = _techs(entities)
    assert len(techs) == 1
    assert techs[0]["canonical_key"] == "postgresql"
    assert techs[0]["name"] == "PostgreSQL"  # first-occurrence verbatim
    assert techs[0]["origin"] == "code_inline"


def test_fenced_code_emits_info_string_only(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    """FR-016g: fenced blocks emit ONE entity keyed on info string; body not mined."""
    text = "```bash\napt install postgresql redis-cli\n```\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    assert len(techs) == 1, "one entity for the fence info string, none for body words"
    assert techs[0]["canonical_key"] == "bash"
    assert techs[0]["origin"] == "fence"


def test_fenced_code_with_empty_info_emits_no_entity(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = "```\nsome content\n```\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    assert techs == []


def test_indented_code_block_emits_no_entity(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    """FR-016g: indented code blocks have no info string → no entity."""
    text = "Regular paragraph.\n\n    indented code with postgresql word\n\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    # Nothing from the indented block (no fence info). No other code in this fixture.
    assert techs == []


def test_casefold_whitespace_dedup_collapses_postgresql_and_postgresql(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Use `PostgreSQL` and also `postgresql` and `POSTGRESQL`.\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    assert len(techs) == 1
    assert techs[0]["canonical_key"] == "postgresql"
    # First occurrence preserved.
    assert techs[0]["name"] == "PostgreSQL"


def test_postgresql_distinct_from_postgresql_16(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = "Use `PostgreSQL` and `PostgreSQL 16`.\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    assert len(techs) == 2
    keys = {t["canonical_key"] for t in techs}
    assert keys == {"postgresql", "postgresql 16"}


def test_postgresql_distinct_from_postgresql_client(redactor: Redactor, empty_index: DocumentsIndex) -> None:
    text = "Use `PostgreSQL` and `postgresql-client`.\n"
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    keys = {t["canonical_key"] for t in techs}
    assert keys == {"postgresql", "postgresql-client"}


def test_technology_dedup_is_per_document_not_global(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    """Per-doc dedup: same token in two different docs → two distinct entities."""
    text = "Use `PostgreSQL`.\n"
    entities_a, _ = _extract(text, redactor, empty_index, source_hash="a" * 64)
    entities_b, _ = _extract(text, redactor, empty_index, source_hash="b" * 64)
    t_a = next(e for e in entities_a if e["type"] == "ag:technology")
    t_b = next(e for e in entities_b if e["type"] == "ag:technology")
    assert t_a["id"] != t_b["id"]
    assert t_a["canonical_key"] == t_b["canonical_key"] == "postgresql"


def test_technology_id_is_source_hash_scoped(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = "Use `PostgreSQL`.\n"
    entities_a, _ = _extract(text, redactor, empty_index, source_hash="a" * 64)
    entities_b, _ = _extract(text, redactor, empty_index, source_hash="b" * 64)
    ta = next(e for e in entities_a if e["type"] == "ag:technology")
    tb = next(e for e in entities_b if e["type"] == "ag:technology")
    assert ta["id"] != tb["id"]


def test_technologies_invariant_i4_unique_canonical_keys(
    redactor: Redactor, empty_index: DocumentsIndex
) -> None:
    text = (FIXTURES / "code_and_links.md").read_text()
    entities, _ = _extract(text, redactor, empty_index)
    techs = _techs(entities)
    keys = [t["canonical_key"] for t in techs]
    assert len(keys) == len(set(keys)), (
        f"I4 violated: duplicate canonical_keys in technologies: {keys}"
    )
