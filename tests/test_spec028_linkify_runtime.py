"""Spec-028 FR-016h · linkify runtime guard tests.

Bare URL detection requires BOTH the `linkify` constructor option AND
the `linkify` rule enabled, AND the `linkify-it-py` package installed
at runtime. These tests are canary guards that fail fast if any of the
three preconditions regresses.
"""
from __future__ import annotations

import pytest
from markdown_it import MarkdownIt


def test_linkify_it_py_is_importable() -> None:
    """Guards against a lockfile / package-data regression."""
    import linkify_it  # noqa: F401 — import is the assertion


def test_bare_url_in_prose_emits_link_tokens() -> None:
    """Authoritative parser config produces link_open/link_close on a bare URL."""
    md = MarkdownIt("commonmark", {"linkify": True}).enable("linkify")
    tokens = md.parse("see https://example.com inline")
    # paragraph_open, inline, paragraph_close — walk the inline children.
    inline = next(t for t in tokens if t.type == "inline")
    children = inline.children or []
    link_opens = [t for t in children if t.type == "link_open"]
    link_closes = [t for t in children if t.type == "link_close"]
    assert link_opens, "bare URL must produce a link_open token when linkify works"
    assert link_closes, "every link_open must have a matching link_close"
    assert link_opens[0].attrGet("href") == "https://example.com"


def test_linkify_option_alone_without_rule_is_insufficient() -> None:
    """Constructor option alone does NOT activate the rule.

    Guards against a future markdown-it-py release that might change this.
    If this test starts passing, the spec may be able to drop the
    `.enable("linkify")` call — at which point this canary should be
    updated to match the new invariant.
    """
    md = MarkdownIt("commonmark", {"linkify": True})  # no .enable
    tokens = md.parse("see https://example.com inline")
    inline = next(t for t in tokens if t.type == "inline")
    children = inline.children or []
    link_opens = [t for t in children if t.type == "link_open"]
    assert not link_opens, (
        "option-only setup unexpectedly produced link_open tokens; if this "
        "is a real behavior change in markdown-it-py, update the authoritative "
        "parser config in contracts/markdown-subentities.md"
    )


def test_enable_rule_alone_without_option_is_insufficient() -> None:
    """`.enable("linkify")` alone without the constructor option no-ops silently."""
    md = MarkdownIt("commonmark").enable("linkify")
    tokens = md.parse("see https://example.com inline")
    inline = next(t for t in tokens if t.type == "inline")
    children = inline.children or []
    link_opens = [t for t in children if t.type == "link_open"]
    # Bare URL is just text here; no link emitted.
    assert not link_opens, (
        "rule-enable-only setup unexpectedly produced link_open tokens; "
        "if this is a real behavior change, update the authoritative config"
    )
