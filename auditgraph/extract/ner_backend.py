"""T003: Thin spaCy NER wrapper with graceful degradation."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_cached_models: dict[str, Any] = {}


def load_ner_model(model_name: str) -> Any:
    """Load a spaCy NER model, caching at module level.

    Returns the spaCy Language object, or None if spaCy/model unavailable.
    """
    if model_name in _cached_models:
        return _cached_models[model_name]
    try:
        import spacy
    except ImportError:
        logger.warning("spaCy is not installed; NER extraction will be skipped.")
        _cached_models[model_name] = None
        return None
    try:
        nlp = spacy.load(model_name)
    except OSError:
        logger.warning("spaCy model '%s' not found. Run: python -m spacy download %s", model_name, model_name)
        _cached_models[model_name] = None
        return None
    _cached_models[model_name] = nlp
    return nlp


def extract_entities_from_text(
    text: str,
    nlp: Any,
    entity_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Run spaCy NER on text. Returns list of entity dicts.

    Each dict has keys: text, label, start, end, score.
    Returns empty list if nlp is None or text is empty.
    """
    if nlp is None or not text:
        return []
    try:
        doc = nlp(text)
    except Exception:
        logger.warning("spaCy NER failed on text of length %d", len(text))
        return []
    results = []
    for ent in doc.ents:
        if entity_types and ent.label_ not in entity_types:
            continue
        results.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char,
            "score": 1.0,  # spaCy sm models don't expose per-entity scores
        })
    return results
