"""Spec-028 FR-016e · Source-cooccurrence type exclusion (invariant I10).

Markdown sub-entities (ag:section / ag:technology / ag:reference) MUST
NOT participate in source-level cooccurrence links. The assertion is
EITHER-endpoint (per adjustments3.md §15) — a link with one markdown
endpoint and one non-markdown endpoint is ALSO a violation.
"""
from __future__ import annotations

from auditgraph.extract.markdown import MARKDOWN_ENTITY_TYPES
from auditgraph.link.rules import EXCLUDED_COOCCURRENCE_TYPES, build_source_cooccurrence_links


def _entity(entity_id: str, entity_type: str, source_path: str = "notes/a.md") -> dict:
    return {
        "id": entity_id,
        "type": entity_type,
        "refs": [{"source_path": source_path, "source_hash": "a" * 64}],
    }


def test_excluded_types_set_matches_markdown_types() -> None:
    assert EXCLUDED_COOCCURRENCE_TYPES == set(MARKDOWN_ENTITY_TYPES)


def test_source_cooccurrence_excludes_ag_section() -> None:
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_sec1", "ag:section"),
    ]
    links = build_source_cooccurrence_links(entities)
    assert links == [], "ag:section participating in cooccurrence violates FR-016e"


def test_source_cooccurrence_excludes_ag_technology() -> None:
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_tech1", "ag:technology"),
    ]
    assert build_source_cooccurrence_links(entities) == []


def test_source_cooccurrence_excludes_ag_reference() -> None:
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_ref1", "ag:reference"),
    ]
    assert build_source_cooccurrence_links(entities) == []


def test_source_cooccurrence_still_emits_for_note_pairs() -> None:
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_note2", "ag:note"),
    ]
    links = build_source_cooccurrence_links(entities)
    # A pair of notes sharing a source still produces bidirectional relates_to.
    assert len(links) == 2
    assert all(link["rule_id"] == "link.source_cooccurrence.v1" for link in links)


def test_no_cooccurrence_link_has_markdown_subentity_on_EITHER_end() -> None:
    """adjustments3.md §15: either-endpoint rule, not both-endpoints."""
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_sec1", "ag:section"),
        _entity("ent_tech1", "ag:technology"),
        _entity("ent_ref1", "ag:reference"),
        _entity("ent_note2", "ag:note"),
    ]
    links = build_source_cooccurrence_links(entities)
    markdown_ids = {"ent_sec1", "ent_tech1", "ent_ref1"}
    for link in links:
        assert link["from_id"] not in markdown_ids, (
            f"I10 violated: {link['from_id']!r} on from side"
        )
        assert link["to_id"] not in markdown_ids, (
            f"I10 violated: {link['to_id']!r} on to side"
        )


def test_mixed_pair_with_one_markdown_subentity_and_one_note_is_rejected() -> None:
    """A section+note pair should NOT produce a relates_to (EITHER endpoint rule)."""
    entities = [
        _entity("ent_note1", "ag:note"),
        _entity("ent_sec1", "ag:section"),
    ]
    links = build_source_cooccurrence_links(entities)
    assert links == [], "mixed markdown+note pair should not produce cooccurrence"
