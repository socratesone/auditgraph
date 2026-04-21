"""Spec-028 US2 · Markdown sub-entity extractor.

Produces deterministic `ag:section`, `ag:technology`, and `ag:reference`
entities from markdown source text, plus the four markdown link rule IDs
that connect them.

This module is the authoritative implementation of
`contracts/markdown-subentities.md` — NOT based on `auditgraph/extract/content.py`
which is an unwired regex-based stub.

Key design points (per data-model.md and the contracts):
- ID inputs are source-scoped (`source_hash::<type>::<key>[::<order>]`).
- Stored `canonical_key` is human-readable (slug path / normalized token /
  redacted raw target) and is DIFFERENT from the ID input.
- Parser setup is `MarkdownIt("commonmark", {"linkify": True}).enable("linkify")`
  — both the constructor option AND the rule enable are required
  (`linkify-it-py` must be installed; Spec-028 FR-016h).
- Pre-heading content (references and technologies appearing before the
  first heading, or in files with no headings) attaches its origin edges
  to `document_anchor_id` (the note entity for this source).
- `DocumentsIndex` is built from the current run's successful ingest
  records only (NOT a disk scan) — callers pass it in; the extractor
  trusts it.
- Images (`![alt](src)`) produce neither `ag:reference` nor `ag:technology`
  entities in v1 (FR-016g).
- Fenced code blocks emit one `ag:technology` keyed on the `info` string
  (language tag); body content is NOT mined. Empty info ⇒ no entity.
- Indented code blocks emit no `ag:technology` (no info string available).

The extractor is pure with respect to the filesystem — it never reads or
writes disk. The caller is the runner, which reads `document.text` and
builds `DocumentsIndex`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt
from markdown_it.token import Token

from auditgraph.storage.hashing import sha256_text
from auditgraph.utils.redaction import Redactor


# ---------------------------------------------------------------------------
# Data structures


@dataclass(frozen=True)
class DocumentsIndex:
    """Bi-directional lookup for reference classification.

    Construction rule (per adjustments3.md §4): build from the CURRENT
    run's normalized ingest records where ``parse_status == "ok"`` —
    NOT from a disk scan of ``documents/``. Stale document artifacts
    from prior runs whose sources were deleted or excluded MUST NOT
    appear here, or references to their paths would falsely classify
    as ``internal``.
    """

    by_doc_id: Mapping[str, Path]
    by_source_path: Mapping[str, str]


# ---------------------------------------------------------------------------
# Rule IDs (authoritative — see data-model.md §2)

RULE_CONTAINS_SECTION = "link.markdown.contains_section.v1"
RULE_MENTIONS_TECHNOLOGY = "link.markdown.mentions_technology.v1"
RULE_REFERENCES = "link.markdown.references.v1"
RULE_RESOLVES_TO_DOCUMENT = "link.markdown.resolves_to_document.v1"

MARKDOWN_ENTITY_TYPES = ("ag:section", "ag:technology", "ag:reference")
MARKDOWN_RULE_IDS = (
    RULE_CONTAINS_SECTION,
    RULE_MENTIONS_TECHNOLOGY,
    RULE_REFERENCES,
    RULE_RESOLVES_TO_DOCUMENT,
)

# FR-016f: URL schemes that classify a reference as "external"
_EXTERNAL_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "mailto"})


# ---------------------------------------------------------------------------
# Parser adapter (FR-016h — both constructor option AND rule enable required)


def _tokenize(text: str) -> list[Token]:
    """Parse markdown into a token stream with linkify enabled.

    Canonical form per `contracts/markdown-subentities.md` §Parser
    configuration. Both the ``linkify`` constructor option and the
    ``.enable("linkify")`` rule activation are required; either alone is
    a silent no-op. ``linkify-it-py`` is required at runtime (pulled in
    by the ``markdown-it-py[linkify]`` extras pin).
    """
    md = MarkdownIt("commonmark", {"linkify": True}).enable("linkify")
    return md.parse(text)


# ---------------------------------------------------------------------------
# Slug rules (data-model.md §1.0)


def _slugify(text: str) -> str:
    """Lowercase; replace every non-word run with '-'; strip surrounding '-'.

    Used for heading `canonical_key` and section `heading_slug_path`.
    Implemented inline here rather than delegating to
    `auditgraph.storage.ontology.canonical_key` because the rules differ
    (we join path components with '/', and the existing helper is single-string).
    """
    out_chars: list[str] = []
    in_word = False
    for ch in text.lower():
        if ch.isalnum() or ch == "_":
            out_chars.append(ch)
            in_word = True
        else:
            if in_word:
                out_chars.append("-")
                in_word = False
    # Strip trailing '-'
    slug = "".join(out_chars).strip("-")
    return slug


# ---------------------------------------------------------------------------
# Reference classification (FR-016f)


def _classify_reference(
    href: str,
    source_path: str,
    documents_index: DocumentsIndex,
) -> tuple[str, str | None]:
    """Return (resolution, target_document_id).

    resolution ∈ {"internal", "external", "unresolved"}.
    target_document_id is set only when resolution == "internal".
    """
    if not href:
        return ("unresolved", None)

    parsed = urlparse(href)

    # Fragment-only → unresolved (in-document anchors out of scope for v1).
    if not parsed.scheme and not parsed.netloc and not parsed.path and parsed.fragment:
        return ("unresolved", None)

    # External: recognized URL scheme.
    if parsed.scheme and parsed.scheme.lower() in _EXTERNAL_SCHEMES:
        return ("external", None)

    # Any other recognized scheme → unresolved (file://, custom schemes).
    if parsed.scheme:
        return ("unresolved", None)

    # Path-based classification. Strip fragment + query; classify on the path only.
    raw_path = parsed.path
    if not raw_path:
        return ("unresolved", None)

    # Directory / bare name (no extension) → unresolved (no README.md auto-resolution in v1).
    decoded = unquote(raw_path)
    if decoded.endswith("/"):
        return ("unresolved", None)
    # Resolve relative to source_path's parent, then workspace-relative.
    source_parent = Path(source_path).parent
    try:
        candidate = (source_parent / decoded).as_posix()
    except Exception:
        return ("unresolved", None)

    # Normalize `./` and `../` by collapsing path components manually.
    # Using PurePosixPath to avoid OS-dependent normalization.
    normalized_parts: list[str] = []
    for part in candidate.split("/"):
        if part == "." or part == "":
            continue
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(part)
    normalized = "/".join(normalized_parts)

    # Directory-style bare name (no file extension at all) ⇒ unresolved.
    last = normalized.rsplit("/", 1)[-1]
    if "." not in last:
        return ("unresolved", None)

    doc_id = documents_index.by_source_path.get(normalized)
    if doc_id:
        return ("internal", doc_id)
    return ("unresolved", None)


# ---------------------------------------------------------------------------
# Link builder


def _link_id(rule_id: str, from_id: str, to_id: str) -> str:
    return f"lnk_{sha256_text(rule_id + ':' + from_id + ':' + to_id)}"


def _build_link(
    *,
    rule_id: str,
    link_type: str,
    from_id: str,
    to_id: str,
    source_path: str,
    source_hash: str,
) -> dict[str, Any]:
    return {
        "id": _link_id(rule_id, from_id, to_id),
        "from_id": from_id,
        "to_id": to_id,
        "type": link_type,
        "rule_id": rule_id,
        "confidence": 1.0,
        "authority": "authoritative",
        "evidence": [{"source_path": source_path, "source_hash": source_hash}],
    }


# ---------------------------------------------------------------------------
# Entity builders


def _build_section_entity(
    *,
    heading_text: str,
    slug_path: str,
    level: int,
    order: int,
    parent_section_id: str | None,
    body_snippet: str,
    source_path: str,
    source_hash: str,
    token_range: tuple[int, int],
    pipeline_version: str,
) -> dict[str, Any]:
    id_input = f"{source_hash}::section::{slug_path}::{order}"
    entity_id = f"ent_{sha256_text(id_input)}"
    return {
        "id": entity_id,
        "type": "ag:section",
        "name": heading_text,
        "canonical_key": slug_path,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.markdown.section.v1",
            "input_hash": source_hash,
            "pipeline_version": pipeline_version,
        },
        "refs": [
            {
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": token_range[0], "end_line": token_range[1]},
            }
        ],
        "body_snippet": body_snippet,
        "level": level,
        "order": order,
        "parent_section_id": parent_section_id,
    }


def _build_technology_entity(
    *,
    normalized_token: str,
    first_seen_text: str,
    origin: str,
    first_seen_order: int,
    source_path: str,
    source_hash: str,
    token_range: tuple[int, int],
    pipeline_version: str,
) -> dict[str, Any]:
    id_input = f"{source_hash}::technology::{normalized_token}"
    entity_id = f"ent_{sha256_text(id_input)}"
    return {
        "id": entity_id,
        "type": "ag:technology",
        "name": first_seen_text,
        "canonical_key": normalized_token,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.markdown.technology.v1",
            "input_hash": source_hash,
            "pipeline_version": pipeline_version,
        },
        "refs": [
            {
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": token_range[0], "end_line": token_range[1]},
            }
        ],
        "first_seen_order": first_seen_order,
        "origin": origin,
    }


def _build_reference_entity(
    *,
    target: str,
    link_text: str,
    order: int,
    resolution: str,
    target_document_id: str | None,
    source_path: str,
    source_hash: str,
    token_range: tuple[int, int],
    pipeline_version: str,
) -> dict[str, Any]:
    id_input = f"{source_hash}::reference::{target}::{order}"
    entity_id = f"ent_{sha256_text(id_input)}"
    return {
        "id": entity_id,
        "type": "ag:reference",
        "name": link_text or target,
        "canonical_key": target,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.markdown.reference.v1",
            "input_hash": source_hash,
            "pipeline_version": pipeline_version,
        },
        "refs": [
            {
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": token_range[0], "end_line": token_range[1]},
            }
        ],
        "target": target,
        "resolution": resolution,
        "target_document_id": target_document_id,
        "order": order,
    }


# ---------------------------------------------------------------------------
# Token-stream walker helpers


def _token_range(token: Token | None) -> tuple[int, int]:
    """Return (start_line, end_line) 1-indexed from the token's map, or (1,1)."""
    if token is None or not token.map:
        return (1, 1)
    # markdown-it map is (start_line, end_line) 0-indexed, end exclusive.
    start = token.map[0] + 1
    end = max(start, token.map[1])
    return (start, end)


def _collect_inline_text(children: Iterable[Token] | None) -> str:
    if not children:
        return ""
    pieces: list[str] = []
    for child in children:
        if child.type == "text" or child.type == "code_inline":
            pieces.append(child.content)
        elif child.type == "softbreak" or child.type == "hardbreak":
            pieces.append(" ")
    return "".join(pieces).strip()


# ---------------------------------------------------------------------------
# Main entry point


def extract_markdown_subentities(
    *,
    source_path: str,
    source_hash: str,
    document_id: str,
    document_anchor_id: str,
    markdown_text: str,
    redactor: Redactor,
    documents_index: DocumentsIndex,
    pipeline_version: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walk a markdown source and emit (entities, links).

    Contract: `contracts/markdown-subentities.md`.
    """
    if not isinstance(markdown_text, str):
        raise ValueError("markdown_text must be a str")
    if not source_hash:
        raise ValueError("source_hash must be non-empty")
    if not document_anchor_id:
        raise ValueError("document_anchor_id must be non-empty")

    tokens = _tokenize(markdown_text)

    entities_by_id: dict[str, dict[str, Any]] = {}
    links: list[dict[str, Any]] = []

    # Section stack entries: (level, entity_id, slug_path)
    section_stack: list[tuple[int, str, str]] = []
    technologies_by_key: dict[str, dict[str, Any]] = {}
    section_order = 0
    reference_order = 0

    def current_origin_id() -> str:
        """Origin for mentions_technology / references edges.

        Rule (FR-016i pre-heading topology): the nearest enclosing section,
        or the document anchor when no section exists yet (pre-heading
        content, or files with no headings).
        """
        if section_stack:
            return section_stack[-1][1]
        return document_anchor_id

    i = 0
    n = len(tokens)
    while i < n:
        token = tokens[i]

        if token.type == "heading_open":
            # The inline token follows; heading_close comes two positions later.
            inline = tokens[i + 1] if i + 1 < n else None
            raw_heading_text = _collect_inline_text(inline.children if inline else None)
            heading_text = redactor.redact_text(raw_heading_text).value

            # Level from tag (h1..h6).
            level = int(token.tag[1]) if token.tag and token.tag.startswith("h") else 1

            # Parent: nearest preceding heading with strictly lower numeric level.
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            parent_section_id = section_stack[-1][1] if section_stack else None

            slug = _slugify(heading_text) or f"section-{section_order}"
            parent_slug_path = section_stack[-1][2] if section_stack else ""
            slug_path = f"{parent_slug_path}/{slug}" if parent_slug_path else slug

            # Body snippet: raw content between this heading and the next
            # heading of equal-or-greater level. Gather up to 512 chars of
            # redacted text.
            body_snippet_raw = _body_snippet_raw(tokens, i, level)
            body_snippet = redactor.redact_text(body_snippet_raw).value[:512]

            entity = _build_section_entity(
                heading_text=heading_text,
                slug_path=slug_path,
                level=level,
                order=section_order,
                parent_section_id=parent_section_id,
                body_snippet=body_snippet,
                source_path=source_path,
                source_hash=source_hash,
                token_range=_token_range(token),
                pipeline_version=pipeline_version,
            )
            entities_by_id[entity["id"]] = entity

            # Emit contains_section link: parent section OR document anchor.
            from_id = parent_section_id if parent_section_id else document_anchor_id
            links.append(
                _build_link(
                    rule_id=RULE_CONTAINS_SECTION,
                    link_type="contains_section",
                    from_id=from_id,
                    to_id=entity["id"],
                    source_path=source_path,
                    source_hash=source_hash,
                )
            )

            section_stack.append((level, entity["id"], slug_path))
            section_order += 1
            # Skip over the heading_open, inline, heading_close triple.
            i += 3
            continue

        if token.type == "fence":
            # Fenced code block: emit one ag:technology keyed on info string.
            info = (token.info or "").strip()
            if info:
                redacted_info = redactor.redact_text(info).value
                normalized = redacted_info.casefold().strip()
                if normalized:
                    if normalized not in technologies_by_key:
                        entity = _build_technology_entity(
                            normalized_token=normalized,
                            first_seen_text=redacted_info,
                            origin="fence",
                            first_seen_order=len(technologies_by_key),
                            source_path=source_path,
                            source_hash=source_hash,
                            token_range=_token_range(token),
                            pipeline_version=pipeline_version,
                        )
                        technologies_by_key[normalized] = entity
                        entities_by_id[entity["id"]] = entity
                    tech_entity = technologies_by_key[normalized]
                    links.append(
                        _build_link(
                            rule_id=RULE_MENTIONS_TECHNOLOGY,
                            link_type="mentions_technology",
                            from_id=current_origin_id(),
                            to_id=tech_entity["id"],
                            source_path=source_path,
                            source_hash=source_hash,
                        )
                    )
            i += 1
            continue

        if token.type == "inline" and token.children:
            # Walk inline children for code_inline and link tokens.
            new_refs, new_tech_links, reference_order = _process_inline_children(
                token.children,
                parent_token=token,
                origin_id=current_origin_id(),
                technologies_by_key=technologies_by_key,
                entities_by_id=entities_by_id,
                documents_index=documents_index,
                source_path=source_path,
                source_hash=source_hash,
                pipeline_version=pipeline_version,
                redactor=redactor,
                document_anchor_id=document_anchor_id,
                reference_order=reference_order,
            )
            links.extend(new_tech_links)
            links.extend(new_refs)
            i += 1
            continue

        i += 1

    # Sort entities for deterministic iteration order when the caller
    # writes them. Links are emitted in walk order which is deterministic
    # already; sorting by link_id stabilizes disk-iteration tests.
    sorted_entities = sorted(entities_by_id.values(), key=lambda e: e["id"])
    sorted_links = sorted(links, key=lambda link: link["id"])
    return sorted_entities, sorted_links


def _body_snippet_raw(tokens: list[Token], start_index: int, heading_level: int) -> str:
    """Concatenate text tokens between this heading and the next heading of
    equal or greater hierarchical level.

    Returns up to ~512 chars of raw text (caller redacts and truncates further).
    """
    pieces: list[str] = []
    char_budget = 1024  # plenty; the caller trims after redaction
    j = start_index + 3  # skip heading_open/inline/heading_close
    while j < len(tokens) and char_budget > 0:
        t = tokens[j]
        if t.type == "heading_open":
            other_level = int(t.tag[1]) if t.tag and t.tag.startswith("h") else 1
            if other_level <= heading_level:
                break
        if t.type == "inline" and t.children:
            text = _collect_inline_text(t.children)
            pieces.append(text)
            char_budget -= len(text)
        elif t.type == "fence":
            fence_text = t.content or ""
            pieces.append(fence_text)
            char_budget -= len(fence_text)
        j += 1
    return " ".join(p for p in pieces if p).strip()


def _process_inline_children(
    children: list[Token],
    *,
    parent_token: Token,
    origin_id: str,
    technologies_by_key: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
    documents_index: DocumentsIndex,
    source_path: str,
    source_hash: str,
    pipeline_version: str,
    redactor: Redactor,
    document_anchor_id: str,
    reference_order: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Walk inline children; emit technology + reference links.

    Returns (reference_links, technology_links, updated_reference_order).
    Image tokens (``image``) are skipped per FR-016g.
    """
    tech_links: list[dict[str, Any]] = []
    ref_links: list[dict[str, Any]] = []

    # Track whether we're inside an image (walk through link_open/close nested in image).
    # markdown-it-py represents `![alt](src)` as a single `image` token with children
    # for alt text. No separate link_open is emitted for images.

    k = 0
    while k < len(children):
        child = children[k]

        if child.type == "code_inline":
            raw_content = child.content or ""
            redacted = redactor.redact_text(raw_content).value
            normalized = redacted.casefold().strip()
            if normalized:
                if normalized not in technologies_by_key:
                    entity = _build_technology_entity(
                        normalized_token=normalized,
                        first_seen_text=redacted,
                        origin="code_inline",
                        first_seen_order=len(technologies_by_key),
                        source_path=source_path,
                        source_hash=source_hash,
                        token_range=_token_range(parent_token),
                        pipeline_version=pipeline_version,
                    )
                    technologies_by_key[normalized] = entity
                    entities_by_id[entity["id"]] = entity
                tech = technologies_by_key[normalized]
                tech_links.append(
                    _build_link(
                        rule_id=RULE_MENTIONS_TECHNOLOGY,
                        link_type="mentions_technology",
                        from_id=origin_id,
                        to_id=tech["id"],
                        source_path=source_path,
                        source_hash=source_hash,
                    )
                )
            k += 1
            continue

        if child.type == "link_open":
            raw_href = child.attrGet("href") or ""
            redacted_href = redactor.redact_text(raw_href).value
            # Accumulate link text until link_close.
            text_pieces: list[str] = []
            m = k + 1
            while m < len(children) and children[m].type != "link_close":
                inner = children[m]
                if inner.type == "text" or inner.type == "code_inline":
                    text_pieces.append(inner.content)
                # Don't recurse into nested links/images (extremely rare in markdown).
                m += 1
            raw_link_text = "".join(text_pieces)
            redacted_link_text = redactor.redact_text(raw_link_text).value

            resolution, target_doc_id = _classify_reference(
                redacted_href, source_path, documents_index
            )

            entity = _build_reference_entity(
                target=redacted_href,
                link_text=redacted_link_text,
                order=reference_order,
                resolution=resolution,
                target_document_id=target_doc_id,
                source_path=source_path,
                source_hash=source_hash,
                token_range=_token_range(parent_token),
                pipeline_version=pipeline_version,
            )
            entities_by_id[entity["id"]] = entity

            ref_links.append(
                _build_link(
                    rule_id=RULE_REFERENCES,
                    link_type="references",
                    from_id=origin_id,
                    to_id=entity["id"],
                    source_path=source_path,
                    source_hash=source_hash,
                )
            )
            if resolution == "internal" and target_doc_id:
                ref_links.append(
                    _build_link(
                        rule_id=RULE_RESOLVES_TO_DOCUMENT,
                        link_type="resolves_to_document",
                        from_id=entity["id"],
                        to_id=target_doc_id,
                        source_path=source_path,
                        source_hash=source_hash,
                    )
                )

            reference_order += 1
            # Skip past link_close if present.
            if m < len(children) and children[m].type == "link_close":
                k = m + 1
            else:
                k = m
            continue

        if child.type == "image":
            # FR-016g v1: images produce no entity. Skip the whole image token.
            k += 1
            continue

        k += 1

    return ref_links, tech_links, reference_order
