"""T005-T007: NER entity extractor — iterate chunks, quality-gate, produce entities and links."""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from auditgraph.storage.hashing import sha256_text
from auditgraph.storage.audit import DEFAULT_PIPELINE_VERSION

logger = logging.getLogger(__name__)

# T006: Case number regex
CASE_NUMBER_PATTERN = re.compile(r'\b\d{2,4}-[A-Z]{2,4}-\d{3,8}\b')

# spaCy label -> auditgraph entity type
_LABEL_MAP: dict[str, str] = {
    "PERSON": "ner:person",
    "ORG": "ner:org",
    "GPE": "ner:gpe",
    "DATE": "ner:date",
    "LAW": "ner:law",
    "MONEY": "ner:money",
}

# Titles to strip during normalization
_TITLE_PATTERN = re.compile(
    r'^(?:Mr\.|Mrs\.|Ms\.|Dr\.|Hon\.|Judge|Attorney)\s+',
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """T007: Canonical name normalization."""
    name = name.strip()
    # Strip titles (iteratively in case of stacking like "Hon. Judge")
    changed = True
    while changed:
        new_name = _TITLE_PATTERN.sub("", name)
        changed = new_name != name
        name = new_name
    # Lowercase
    name = name.lower()
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    # Strip trailing punctuation
    name = name.rstrip('.,;:!?')
    return name


def _text_quality(text: str) -> float:
    """Compute text quality score: ratio of alphanumeric characters."""
    if not text:
        return 0.0
    alnum_count = len([c for c in text if c.isalnum()])
    return alnum_count / max(len(text), 1)


def _ner_entity_id(canonical_key: str) -> str:
    """Deterministic entity ID for NER entities."""
    return f"ent_{sha256_text(canonical_key)}"


def _ner_link_id(key: str) -> str:
    """Deterministic link ID."""
    return f"lnk_{sha256_text(key)}"


def extract_ner_entities(
    pkg_root: Path,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract NER entities from chunks. Returns (entities, links).

    Config keys:
        enabled: bool
        model: str (spaCy model name)
        quality_threshold: float
        entity_types: list[str] (spaCy labels to extract)
        cooccurrence_types: list[str] (labels for CO_OCCURS_WITH)
    """
    if not config.get("enabled", False):
        return [], []

    model_name = config.get("model", "en_core_web_sm")
    quality_threshold = float(config.get("quality_threshold", 0.3))
    allowed_types = set(config.get("entity_types", list(_LABEL_MAP.keys())))
    cooccurrence_types = set(config.get("cooccurrence_types", ["PERSON", "ORG", "GPE"]))

    from auditgraph.extract.ner_backend import load_ner_model, extract_entities_from_text

    nlp = load_ner_model(model_name)
    if nlp is None:
        logger.warning("NER model not available; skipping NER extraction.")
        return [], []

    # Load all chunk JSON files
    chunks_dir = pkg_root / "chunks"
    if not chunks_dir.exists():
        return [], []

    chunk_files = sorted(chunks_dir.rglob("*.json"))
    if not chunk_files:
        return [], []

    # Track mentions: key=(ner_type, normalized_name) -> {surface_forms, chunks, refs}
    mentions: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
        "surface_forms": set(),
        "chunk_ids": set(),
        "refs": [],
        "mention_count": 0,
    })

    # Track which entities appear in which chunk (for co-occurrence)
    chunk_entity_keys: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for chunk_file in chunk_files:
        try:
            chunk = json.loads(chunk_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id", chunk.get("id", ""))
        if not text or not chunk_id:
            continue

        # Quality gate
        if _text_quality(text) < quality_threshold:
            continue

        source_path = chunk.get("source_path", "")
        source_hash = chunk.get("source_hash", "")

        # Run spaCy NER
        spacy_entities = extract_entities_from_text(text, nlp, entity_types=allowed_types)
        for ent in spacy_entities:
            label = ent["label"]
            if label not in _LABEL_MAP:
                continue
            ner_type = _LABEL_MAP[label]
            normalized = _normalize_name(ent["text"])
            if not normalized:
                continue
            key = (ner_type, normalized)
            mentions[key]["surface_forms"].add(ent["text"])
            mentions[key]["chunk_ids"].add(chunk_id)
            mentions[key]["mention_count"] += 1
            mentions[key]["refs"].append({
                "source_path": source_path,
                "source_hash": source_hash,
                "chunk_id": chunk_id,
            })
            chunk_entity_keys[chunk_id].add(key)

        # Run case number regex
        case_matches = CASE_NUMBER_PATTERN.findall(text)
        for case_num in case_matches:
            normalized = case_num.strip()
            key = ("ner:case_number", normalized.lower())
            mentions[key]["surface_forms"].add(case_num)
            mentions[key]["chunk_ids"].add(chunk_id)
            mentions[key]["mention_count"] += 1
            mentions[key]["refs"].append({
                "source_path": source_path,
                "source_hash": source_hash,
                "chunk_id": chunk_id,
            })
            chunk_entity_keys[chunk_id].add(key)

    # Build entity dicts
    entities: list[dict[str, Any]] = []
    entity_id_map: dict[tuple[str, str], str] = {}

    for (ner_type, normalized), data in mentions.items():
        canonical_key_str = f"ner:{ner_type}:{normalized}" if not ner_type.startswith("ner:") else f"{ner_type}:{normalized}"
        # The canonical_key format is "ner:<type_suffix>:<name>" but ner_type already has "ner:" prefix
        # So canonical_key = "ner:person:john smith" etc.
        # But ner_type is already "ner:person", so canonical_key = "ner:person:john smith"
        canonical_key_str = f"{ner_type}:{normalized}"
        entity_id = _ner_entity_id(canonical_key_str)
        entity_id_map[(ner_type, normalized)] = entity_id

        # Canonical name = longest surface form
        surface_forms = sorted(data["surface_forms"], key=lambda s: (-len(s), s))
        canonical_name = surface_forms[0] if surface_forms else normalized

        # Deduplicate refs by chunk_id
        seen_refs: set[str] = set()
        unique_refs = []
        for ref in data["refs"]:
            ref_key = ref.get("chunk_id", "")
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                unique_refs.append(ref)

        entity = {
            "id": entity_id,
            "type": ner_type,
            "name": canonical_name,
            "canonical_key": canonical_key_str,
            "aliases": sorted(data["surface_forms"]),
            "mention_count": data["mention_count"],
            "provenance": {
                "created_by_rule": "ner.spacy.v1",
                "model": model_name,
                "pipeline_version": DEFAULT_PIPELINE_VERSION,
            },
            "refs": unique_refs,
        }
        entities.append(entity)

    # Build MENTIONED_IN links
    links: list[dict[str, Any]] = []
    for (ner_type, normalized), data in mentions.items():
        entity_id = entity_id_map[(ner_type, normalized)]
        for chunk_id in sorted(data["chunk_ids"]):
            link_key = f"ner.mention.v1:{entity_id}:{chunk_id}"
            link = {
                "id": _ner_link_id(link_key),
                "from_id": entity_id,
                "to_id": chunk_id,
                "type": "MENTIONED_IN",
                "rule_id": "ner.mention.v1",
                "confidence": 1.0,
                "evidence": [],
                "authority": "ner",
            }
            links.append(link)

    # Build CO_OCCURS_WITH links
    cooccurrence_ner_types = {_LABEL_MAP.get(t, f"ner:{t.lower()}") for t in cooccurrence_types}
    seen_pairs: set[tuple[str, str]] = set()

    for chunk_id, entity_keys in chunk_entity_keys.items():
        # Filter to cooccurrence-eligible types
        eligible = [(k, entity_id_map[k]) for k in entity_keys if k[0] in cooccurrence_ner_types]
        eligible.sort(key=lambda x: x[1])  # sort by entity_id

        for i in range(len(eligible)):
            for j in range(i + 1, len(eligible)):
                eid_a = eligible[i][1]
                eid_b = eligible[j][1]
                # Canonical order
                from_id, to_id = (eid_a, eid_b) if eid_a <= eid_b else (eid_b, eid_a)
                pair = (from_id, to_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                link_key = f"ner.cooccurrence.v1:{from_id}:{to_id}"
                link = {
                    "id": _ner_link_id(link_key),
                    "from_id": from_id,
                    "to_id": to_id,
                    "type": "CO_OCCURS_WITH",
                    "rule_id": "ner.cooccurrence.v1",
                    "confidence": 1.0,
                    "evidence": [],
                    "authority": "ner",
                }
                links.append(link)

    logger.info("NER extraction: %d entities, %d links", len(entities), len(links))
    return entities, links
