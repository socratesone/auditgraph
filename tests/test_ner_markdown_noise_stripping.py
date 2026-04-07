"""Tests for stripping markdown noise from NER input.

The default `en_core_web_sm` spaCy model misclassifies markdown
formatting tokens as named entities. Specifically, citation tokens
like `citeturn1search7` look like proper nouns / numbers to the model
and end up tagged as ner:money or ner:person. Heading markers (`#`,
`##`, ...) and inline code spans (`backtick-text-backtick`) also leak
through.

This module verifies that a noise-stripping helper removes these
patterns from the chunk text BEFORE it's passed to spaCy, eliminating
the worst category of NER false positives at near-zero cost.
"""
from __future__ import annotations

import pytest


# Implementation lives in auditgraph.extract.ner.
# We import the helper directly so we can unit-test it without spinning
# up the full extract pipeline.
from auditgraph.extract.ner import strip_markdown_noise


class TestStripMarkdownNoise:
    """Unit tests for `strip_markdown_noise(text: str) -> str`."""

    def test_passes_plain_prose_unchanged(self):
        text = "Alice met Bob at the cafe yesterday."
        assert strip_markdown_noise(text) == text

    def test_strips_citeturn_citation_tokens(self):
        # The markdown research paper format injects tokens like
        # `citeturn1search7turn8search13turn8search15` into the body.
        text = "The Whisper model is described in citeturn1search7 and benchmarks are in citeturn8search13."
        cleaned = strip_markdown_noise(text)
        assert "citeturn" not in cleaned
        assert "Whisper" in cleaned  # real content preserved
        assert "model" in cleaned

    def test_strips_citeturn_with_multiple_segments(self):
        text = "Recent work citeturn13search18turn13search3turn13search22 covers ASR systems."
        cleaned = strip_markdown_noise(text)
        assert "citeturn" not in cleaned
        assert "ASR" in cleaned

    def test_strips_atx_heading_markers(self):
        text = "## Recommendations\n\nUse Whisper for batch transcription."
        cleaned = strip_markdown_noise(text)
        assert "##" not in cleaned
        assert "Recommendations" in cleaned
        assert "Whisper" in cleaned

    def test_strips_deep_heading_markers(self):
        text = "###### Deep heading\n\nBody text."
        cleaned = strip_markdown_noise(text)
        assert "######" not in cleaned
        assert "Deep heading" in cleaned

    def test_strips_inline_code_spans(self):
        text = "Use the `auditgraph rebuild` command to regenerate."
        cleaned = strip_markdown_noise(text)
        # The backticks should be gone; the inner content stays
        assert "`" not in cleaned
        assert "auditgraph rebuild" in cleaned

    def test_strips_fenced_code_blocks(self):
        text = (
            "Run this:\n"
            "```bash\n"
            "auditgraph rebuild\n"
            "```\n"
            "Then check the output."
        )
        cleaned = strip_markdown_noise(text)
        # The triple-backtick fences should be gone
        assert "```" not in cleaned
        # Content of the code block can stay (it's still text)
        assert "Then check the output" in cleaned

    def test_strips_link_syntax_keeps_link_text(self):
        text = "See [the docs](https://example.com/docs) for details."
        cleaned = strip_markdown_noise(text)
        assert "[" not in cleaned
        assert "]" not in cleaned
        assert "(https://example.com/docs)" not in cleaned
        assert "the docs" in cleaned
        assert "for details" in cleaned

    def test_strips_image_syntax(self):
        text = "Architecture: ![diagram](images/arch.png)"
        cleaned = strip_markdown_noise(text)
        assert "![" not in cleaned
        # The alt text "diagram" should remain or be removed; either is fine
        # as long as the markdown syntax tokens are gone
        assert "Architecture" in cleaned

    def test_strips_bold_and_italic_markers(self):
        text = "This is **bold** and *italic* and __also bold__."
        cleaned = strip_markdown_noise(text)
        assert "**" not in cleaned
        assert "__" not in cleaned
        # Single asterisk for italic must be removed too
        assert "*italic*" not in cleaned
        assert "bold" in cleaned
        assert "italic" in cleaned
        assert "also bold" in cleaned

    def test_does_not_eat_punctuation_in_real_text(self):
        text = "Dr. Smith said, 'This is important.'"
        cleaned = strip_markdown_noise(text)
        assert "Dr. Smith" in cleaned
        assert "important" in cleaned

    def test_handles_empty_string(self):
        assert strip_markdown_noise("") == ""

    def test_handles_text_with_only_markdown_noise(self):
        # All-noise input: heading markers at line start, code fences,
        # citation tokens. Fenced code blocks are dropped entirely
        # (content included) per the docstring contract.
        text = "## Heading\n## Another heading\n```\nbody\n```\nciteturn1search1"
        cleaned = strip_markdown_noise(text)
        # Line-start heading markers should be gone
        assert not any(line.startswith("##") for line in cleaned.split("\n"))
        assert "```" not in cleaned
        assert "citeturn" not in cleaned
        # Heading text should still be present (only the # markers are stripped)
        assert "Heading" in cleaned

    def test_fenced_code_block_content_is_dropped(self):
        """Per the docstring, fenced code blocks are dropped entirely.
        Their content is treated as noise for NER purposes."""
        text = "Before.\n```python\nx = compute(42)\n```\nAfter."
        cleaned = strip_markdown_noise(text)
        assert "```" not in cleaned
        assert "compute" not in cleaned  # body is dropped
        assert "Before" in cleaned
        assert "After" in cleaned

    def test_real_world_research_paper_snippet(self):
        """A realistic snippet combining several noise patterns."""
        text = (
            "## Streaming vs batch\n\n"
            "**Streaming ASR** demands low end-to-end latency and stable "
            "partial hypotheses. citeturn0search4turn1search1turn1search7 "
            "Cloud products explicitly separate `real-time` vs `batch` "
            "modes. citeturn11search1turn11search2turn10search9"
        )
        cleaned = strip_markdown_noise(text)
        assert "##" not in cleaned
        assert "**" not in cleaned
        assert "`" not in cleaned
        assert "citeturn" not in cleaned
        assert "Streaming ASR" in cleaned
        assert "real-time" in cleaned
        assert "batch" in cleaned
