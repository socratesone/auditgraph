"""Tests for the post-extraction NER quality filter.

The default spaCy `en_core_web_sm` model misclassifies many short or
all-caps tokens as named entities. Even after markdown noise stripping
(Phase 2), the model still produces false positives like:

  - "Edge", "Bias", "Training" tagged as ner:person
  - "GPU", "CPU", "RNN" tagged as ner:org
  - "$", "%" or numeric tokens lacking currency markers tagged as ner:money

This module verifies a configurable post-extraction filter that drops
the most common categories of noise based on simple, language-agnostic
heuristics. The filter is opt-in (enabled by default but each rule can
be disabled or tuned via config) so it can be turned off for content
where it would over-filter.
"""
from __future__ import annotations

import pytest

from auditgraph.extract.ner import filter_low_quality_entities


def _entity(name: str, ner_type: str, mention_count: int = 1) -> dict:
    """Build a minimal entity dict for filter tests."""
    return {
        "id": f"ent_{name.lower().replace(' ', '_')}",
        "type": ner_type,
        "name": name,
        "canonical_key": f"{ner_type}:{name.lower()}",
        "aliases": [name],
        "mention_count": mention_count,
        "refs": [],
    }


# ---------------------------------------------------------------------------
# Person filter
# ---------------------------------------------------------------------------


class TestPersonEntityFilter:
    """Default rule: drop ner:person entities whose name is a single word."""

    def test_two_word_person_name_passes(self):
        ents = [_entity("John Smith", "ner:person")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1
        assert kept[0]["name"] == "John Smith"

    def test_three_word_person_name_passes(self):
        ents = [_entity("Mary Jane Watson", "ner:person")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_single_word_person_dropped_by_default(self):
        ents = [_entity("Bias", "ner:person")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_single_word_person_dropped_even_with_high_mention_count(self):
        """Mention count alone shouldn't override the single-word heuristic."""
        ents = [_entity("Edge", "ner:person", mention_count=42)]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_user_can_disable_person_filter(self):
        ents = [_entity("Bias", "ner:person")]
        kept = filter_low_quality_entities(ents, min_person_words=1)
        assert len(kept) == 1

    def test_user_can_require_three_word_persons(self):
        ents = [
            _entity("John Smith", "ner:person"),
            _entity("Mary Jane Watson", "ner:person"),
        ]
        kept = filter_low_quality_entities(ents, min_person_words=3)
        names = {e["name"] for e in kept}
        assert names == {"Mary Jane Watson"}


# ---------------------------------------------------------------------------
# Organization filter
# ---------------------------------------------------------------------------


class TestOrgEntityFilter:
    """Default rule: drop ner:org entities that are short all-caps tokens
    (e.g., 'GPU', 'CPU', 'RNN'). These are technical acronyms misclassified
    as organization names by news-trained NER models."""

    def test_real_org_name_passes(self):
        ents = [_entity("OpenAI", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_multiword_org_passes(self):
        ents = [_entity("Mozilla Foundation", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_short_acronym_org_dropped_by_default(self):
        ents = [_entity("GPU", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_three_letter_acronym_org_dropped(self):
        ents = [_entity("RNN", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_long_acronym_passes(self):
        """6+ char all-caps tokens often ARE legitimate orgs (NASA, CERN are short
        but UNESCO, UNICEF are still acronyms — we drop short ones, keep long ones).
        Our default cutoff is 4 chars: tokens of 4 or fewer chars get dropped."""
        ents = [_entity("UNESCO", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_mixed_case_short_org_passes(self):
        """Short but mixed-case orgs are not the false-positive pattern we
        target — they're likely real names like 'IBM' (well, IBM is also
        all-caps, but 'iOS' or 'eBay' are not). We only drop short
        ALL-CAPS tokens."""
        ents = [_entity("iOS", "ner:org")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_user_can_disable_org_filter(self):
        ents = [_entity("GPU", "ner:org")]
        kept = filter_low_quality_entities(ents, max_short_acronym_org_length=0)
        assert len(kept) == 1

    def test_user_can_tune_org_acronym_length(self):
        # Drop only 1-3 char acronyms; keep 4+
        ents = [
            _entity("AI", "ner:org"),    # 2 chars, dropped
            _entity("CTC", "ner:org"),   # 3 chars, dropped
            _entity("LSTM", "ner:org"),  # 4 chars, kept
        ]
        kept = filter_low_quality_entities(ents, max_short_acronym_org_length=3)
        names = {e["name"] for e in kept}
        assert names == {"LSTM"}


# ---------------------------------------------------------------------------
# Money filter
# ---------------------------------------------------------------------------


class TestMoneyEntityFilter:
    """Default rule: drop ner:money entities that lack a currency marker
    (no $, €, £, ¥, no 'USD'/'EUR'/etc., no 'dollars'/'euros'/etc.)."""

    def test_dollar_amount_passes(self):
        ents = [_entity("$1.5 million", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_euro_amount_passes(self):
        ents = [_entity("€500", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_pound_amount_passes(self):
        ents = [_entity("£100", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_usd_marker_passes(self):
        ents = [_entity("100 USD", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_dollars_word_passes(self):
        ents = [_entity("five hundred dollars", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_bare_number_dropped(self):
        ents = [_entity("100", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_markdown_marker_dropped(self):
        """Markdown heading markers like '###' get tagged as money. Drop."""
        ents = [_entity("###", "ner:money")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 0

    def test_user_can_disable_money_filter(self):
        ents = [_entity("100", "ner:money")]
        kept = filter_low_quality_entities(ents, require_money_currency_marker=False)
        assert len(kept) == 1


# ---------------------------------------------------------------------------
# Other entity types should be untouched
# ---------------------------------------------------------------------------


class TestNonTargetEntitiesUntouched:
    def test_dates_pass_through(self):
        ents = [_entity("2026-04-07", "ner:date")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_gpe_passes_through(self):
        ents = [_entity("New York", "ner:gpe")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1

    def test_law_passes_through(self):
        ents = [_entity("Title VII", "ner:law")]
        kept = filter_low_quality_entities(ents)
        assert len(kept) == 1


# ---------------------------------------------------------------------------
# Combined / mixed inputs
# ---------------------------------------------------------------------------


class TestMixedEntityFiltering:
    def test_real_world_research_paper_entities(self):
        """A representative mix of real entities and false positives from a
        research paper. After filtering, only the real entities should remain."""
        ents = [
            # Real entities — should pass
            _entity("OpenAI", "ner:org"),
            _entity("Mozilla", "ner:org"),
            _entity("Yann LeCun", "ner:person"),
            _entity("New York", "ner:gpe"),
            # False positives — should be dropped
            _entity("GPU", "ner:org"),
            _entity("CPU", "ner:org"),
            _entity("RNN", "ner:org"),
            _entity("Whisper", "ner:person"),
            _entity("Bias", "ner:person"),
            _entity("Training", "ner:person"),
            _entity("###", "ner:money"),
            _entity("100", "ner:money"),
        ]
        kept = filter_low_quality_entities(ents)
        kept_names = {e["name"] for e in kept}

        assert "OpenAI" in kept_names
        assert "Mozilla" in kept_names
        assert "Yann LeCun" in kept_names
        assert "New York" in kept_names

        assert "GPU" not in kept_names
        assert "CPU" not in kept_names
        assert "RNN" not in kept_names
        assert "Whisper" not in kept_names
        assert "Bias" not in kept_names
        assert "Training" not in kept_names
        assert "###" not in kept_names
        assert "100" not in kept_names

    def test_returns_empty_list_when_all_filtered(self):
        ents = [
            _entity("GPU", "ner:org"),
            _entity("Bias", "ner:person"),
            _entity("###", "ner:money"),
        ]
        kept = filter_low_quality_entities(ents)
        assert kept == []

    def test_returns_input_list_when_filter_disabled(self):
        ents = [
            _entity("GPU", "ner:org"),
            _entity("Bias", "ner:person"),
            _entity("###", "ner:money"),
        ]
        kept = filter_low_quality_entities(
            ents,
            min_person_words=1,
            max_short_acronym_org_length=0,
            require_money_currency_marker=False,
        )
        assert len(kept) == 3
