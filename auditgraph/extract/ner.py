"""T005-T007: NER entity extractor — iterate chunks, quality-gate, produce entities and links."""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from auditgraph.storage.hashing import entity_id as _ner_entity_id, sha256_text
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

# Default natural-language file extensions. NER inference is meaningful only on
# natural-language content; on code files it produces mostly false-positive
# entities (variable and function names matching PERSON/ORG patterns) at high
# inference cost. Users can override this list via the
# `extraction.ner.natural_language_extensions` config key.
DEFAULT_NATURAL_LANGUAGE_EXTENSIONS: tuple[str, ...] = (
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".pdf",
    ".docx",
)


# Markdown noise patterns. These tokens look entity-shaped to spaCy's
# `en_core_web_sm` model and produce false-positive ner:money / ner:person /
# ner:org entries when left in the NER input. Stripping them before inference
# eliminates the worst category of false positives at near-zero cost.
#
# Pattern order matters: fenced code blocks must be stripped before inline
# code spans (which would otherwise consume the closing triple-backtick).
_MD_FENCED_CODE_BLOCK = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
_MD_FENCED_CODE_FENCE_LINE = re.compile(r"^```[^\n]*$", re.MULTILINE)
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_BOLD_DOUBLE_STAR = re.compile(r"\*\*([^*]+?)\*\*")
_MD_BOLD_DOUBLE_UNDERSCORE = re.compile(r"__([^_]+?)__")
_MD_ITALIC_SINGLE_STAR = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?![*\w])")
# Citation tokens specific to research-paper markdown exports, e.g.
# `citeturn1search7turn8search13`. The model treats these as currency-like
# numeric tokens and assigns them ner:money or ner:person.
#
# Implementation notes:
# - Case-sensitive: research-paper exports use lowercase `cite` literally.
#   IGNORECASE would cause the inner [a-z0-9] class to also match
#   uppercase letters, which would let the greedy [a-z0-9]+ consume the
#   following word (e.g. `Latency` after `citeturn8search0turn3search1`).
# - No trailing \b: a citation token can be glued directly to the next
#   word with no separator (e.g. `citeturn8search0turn3search1Latency`).
#   The case-sensitive [a-z0-9] class naturally stops at the uppercase
#   start of the next word.
_MD_CITETURN = re.compile(r"\bcite(?:turn[a-z0-9]+)+")


# Currency markers used by the post-extraction money filter. Lowercased
# substrings that, if present anywhere in the entity name, mark it as a
# real money entity rather than a bare number or markdown noise.
_MONEY_CURRENCY_SYMBOLS = {"$", "€", "£", "¥", "₹", "¢"}
_MONEY_CURRENCY_WORDS = {
    "usd", "eur", "gbp", "jpy", "inr", "aud", "cad", "chf", "cny",
    "dollar", "dollars", "euro", "euros", "pound", "pounds", "yen",
    "rupee", "rupees", "cent", "cents", "buck", "bucks",
}


def _name_has_money_marker(name: str) -> bool:
    """Return True if `name` contains a recognized currency symbol or word."""
    if not name:
        return False
    if any(sym in name for sym in _MONEY_CURRENCY_SYMBOLS):
        return True
    lowered = name.lower()
    # Word-boundary check for currency words to avoid matching
    # "documentation" containing "doc" → no, that's not in the list anyway.
    # We just check substrings; the word list is short and unambiguous.
    return any(word in lowered for word in _MONEY_CURRENCY_WORDS)


def filter_low_quality_entities(
    entities: list[dict],
    *,
    min_person_words: int = 2,
    max_short_acronym_org_length: int = 4,
    require_money_currency_marker: bool = True,
) -> list[dict]:
    """Drop NER entities that match common false-positive patterns.

    The default `en_core_web_sm` model produces a high false-positive
    rate on technical content: short acronyms get tagged as ORG, common
    concept words get tagged as PERSON, and numeric/markdown tokens get
    tagged as MONEY. This filter applies simple heuristics to drop the
    obvious false positives. Each rule is configurable so callers can
    tune or disable individual filters for content where they would
    over-filter.

    Args:
        entities: NER entity dicts produced by `extract_ner_entities`.
        min_person_words: drop ner:person entities whose name has fewer
            than this many whitespace-separated words. Default 2 catches
            single-word concept words like "Bias", "Training". Set to 1
            to disable the person filter.
        max_short_acronym_org_length: drop ner:org entities whose name is
            an all-uppercase token of this length or fewer characters.
            Default 4 catches "GPU", "CPU", "RNN", "WER". Set to 0 to
            disable the org filter. Mixed-case names ("iOS", "OpenAI")
            are unaffected regardless of length.
        require_money_currency_marker: drop ner:money entities whose name
            doesn't contain a currency symbol ($, €, £, ¥, ₹, ¢) or a
            currency word (USD, EUR, dollar, euro, etc.). Default True
            catches markdown markers like "###" and bare numbers like
            "100". Set to False to disable the money filter.

    Returns:
        A new list containing only the entities that survived all
        applicable filters. Non-NER entity types and entity types not
        targeted by any filter (date, gpe, law, etc.) pass through
        unchanged.
    """
    out: list[dict] = []
    for entity in entities:
        ner_type = str(entity.get("type", ""))
        name = str(entity.get("name", ""))

        if ner_type == "ner:person":
            if min_person_words > 1:
                word_count = len(name.split())
                if word_count < min_person_words:
                    continue

        elif ner_type == "ner:org":
            if max_short_acronym_org_length > 0:
                # Drop short, all-uppercase tokens (e.g., "GPU", "RNN").
                # Mixed-case orgs and longer all-caps orgs (UNESCO, UNICEF) pass.
                if name.isupper() and len(name) <= max_short_acronym_org_length:
                    continue

        elif ner_type == "ner:money":
            if require_money_currency_marker:
                if not _name_has_money_marker(name):
                    continue

        out.append(entity)
    return out


def strip_markdown_noise(text: str) -> str:
    """Remove markdown formatting noise that confuses NER models.

    Strips citation tokens, heading markers, code fences and inline code
    spans, link/image syntax, and bold/italic emphasis markers. Preserves
    the human-readable content inside these constructs (link text, code
    body, heading text, etc.) so the underlying meaning still reaches NER.

    Also strips Unicode private-use area (PUA) characters (U+E000-U+F8FF).
    Some research-paper markdown exporters wrap citation tokens in PUA
    delimiters as invisible markers. Removing them first lets the
    citation regex match the now-contiguous text.

    Order is significant: fenced code blocks are stripped first so their
    triple-backtick fences don't get matched by the inline code pattern.
    PUA chars are stripped before citation tokens so the citation pattern
    sees the literal token text.
    """
    if not text:
        return text

    # 0. Drop Unicode private-use area characters used as invisible
    # delimiters by some markdown exporters around citation tokens.
    out = re.sub(r"[\ue000-\uf8ff]", "", text)
    # 1. Drop fenced code blocks entirely (content + fences) — code body is
    # noise for NER even if you preserved it as inline text.
    out = _MD_FENCED_CODE_BLOCK.sub("\n", out)
    # 2. Drop any leftover bare ``` lines from unbalanced/odd fences.
    out = _MD_FENCED_CODE_FENCE_LINE.sub("", out)
    # 3. Inline code -> bare content (drop the backticks).
    out = _MD_INLINE_CODE.sub(r"\1", out)
    # 4. Image syntax -> alt text only.
    out = _MD_IMAGE.sub(r"\1", out)
    # 5. Link syntax -> link text only (drop the URL).
    out = _MD_LINK.sub(r"\1", out)
    # 6. ATX heading markers -> drop the leading hashes (keep the heading text).
    out = _MD_HEADING.sub("", out)
    # 7. Bold (**X** and __X__) -> bare content.
    out = _MD_BOLD_DOUBLE_STAR.sub(r"\1", out)
    out = _MD_BOLD_DOUBLE_UNDERSCORE.sub(r"\1", out)
    # 8. Italic single-star -> bare content. Done after bold so we don't
    # eat the inner content of an unprocessed bold pair.
    out = _MD_ITALIC_SINGLE_STAR.sub(r"\1", out)
    # 9. Research-paper citation tokens -> drop entirely.
    out = _MD_CITETURN.sub("", out)
    # 10. Collapse multiple consecutive blank lines / whitespace runs that
    # the substitutions above may have produced. Single blank line preserved
    # so paragraph structure is still legible to spaCy's sentencer.
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]+", " ", out)
    return out.strip()


def _is_natural_language_source(source_path: str, allowed_extensions: set[str]) -> bool:
    """Return True if the chunk's source file is a natural-language document.

    Empty source_path is treated as natural-language (safe default for legacy
    chunks that pre-date this filter). Files with no extension or unknown
    extensions are skipped. Extension comparison is case-insensitive.
    """
    if not source_path:
        return True
    if "." not in source_path.rsplit("/", 1)[-1]:
        # No extension at all (e.g., "Makefile", "Dockerfile")
        return False
    ext = "." + source_path.rsplit(".", 1)[-1].lower()
    return ext in allowed_extensions


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
    nl_extensions = {
        ext.lower()
        for ext in config.get("natural_language_extensions", DEFAULT_NATURAL_LANGUAGE_EXTENSIONS)
    }
    # Post-extraction filter config (Issue 3 Phase 3). Each rule is on by
    # default but can be tuned or disabled. See `filter_low_quality_entities`
    # for the precise semantics of each parameter.
    filter_enabled = bool(config.get("filter_low_quality", True))
    min_person_words = int(config.get("min_person_words", 2))
    max_short_acronym_org_length = int(config.get("max_short_acronym_org_length", 4))
    require_money_currency_marker = bool(config.get("require_money_currency_marker", True))

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

        # Skip non-natural-language chunks (e.g., source code, build files).
        # NER inference on code is expensive and produces mostly false positives
        # from variable and function names. See DEFAULT_NATURAL_LANGUAGE_EXTENSIONS.
        if not _is_natural_language_source(source_path, nl_extensions):
            continue

        # Strip markdown formatting noise (citation tokens, heading markers,
        # code fences, link/image syntax, emphasis markers) before NER. These
        # tokens look entity-shaped to spaCy's en_core_web_sm and produce a
        # large fraction of the false positives observed on technical content.
        # The stripped text preserves real content but removes formatting
        # tokens that have no semantic meaning.
        ner_input_text = strip_markdown_noise(text)
        if not ner_input_text:
            continue

        # Run spaCy NER on the stripped text
        spacy_entities = extract_entities_from_text(ner_input_text, nlp, entity_types=allowed_types)
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
                "span_start": ent["start"],
                "span_end": ent["end"],
                "surface_form": ent["text"],
                "score": ent["score"],
            })
            chunk_entity_keys[chunk_id].add(key)

        # Run case number regex
        for match in CASE_NUMBER_PATTERN.finditer(text):
            case_num = match.group()
            normalized = case_num.strip()
            key = ("ner:case_number", normalized.lower())
            mentions[key]["surface_forms"].add(case_num)
            mentions[key]["chunk_ids"].add(chunk_id)
            mentions[key]["mention_count"] += 1
            mentions[key]["refs"].append({
                "source_path": source_path,
                "source_hash": source_hash,
                "chunk_id": chunk_id,
                "span_start": match.start(),
                "span_end": match.end(),
                "surface_form": case_num,
                "score": 1.0,
            })
            chunk_entity_keys[chunk_id].add(key)

    # Build entity dicts
    entities: list[dict[str, Any]] = []
    entity_id_map: dict[tuple[str, str], str] = {}

    for (ner_type, normalized), data in mentions.items():
        # Canonical key format: "<ner_type>:<normalized_name>", e.g. "ner:person:john smith"
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

    # Apply post-extraction quality filter (Issue 3 Phase 3). Rules drop the
    # most common spaCy en_core_web_sm false positives on technical content:
    # short acronym ner:org, single-word ner:person, ner:money without a
    # currency marker. Filtered entities AND any links involving them are
    # dropped together so the graph stays consistent.
    if filter_enabled:
        entities = filter_low_quality_entities(
            entities,
            min_person_words=min_person_words,
            max_short_acronym_org_length=max_short_acronym_org_length,
            require_money_currency_marker=require_money_currency_marker,
        )
        # Build the set of surviving entity IDs so the link-builders below
        # can skip references to dropped entities.
        surviving_entity_ids = {str(e["id"]) for e in entities}
    else:
        surviving_entity_ids = {str(e["id"]) for e in entities}

    # Build MENTIONED_IN links — one per individual mention span for full provenance
    links: list[dict[str, Any]] = []
    seen_link_ids: set[str] = set()
    for (ner_type, normalized), data in mentions.items():
        entity_id = entity_id_map[(ner_type, normalized)]
        if entity_id not in surviving_entity_ids:
            continue
        for ref in data["refs"]:
            chunk_id = ref["chunk_id"]
            span_start = ref["span_start"]
            span_end = ref["span_end"]
            surface_form = ref["surface_form"]
            score = ref["score"]
            link_key = f"ner.mention.v1:{entity_id}:{chunk_id}:{span_start}"
            link_id = _ner_link_id(link_key)
            if link_id not in seen_link_ids:
                seen_link_ids.add(link_id)
                links.append({
                    "id": link_id,
                    "from_id": entity_id,
                    "to_id": chunk_id,
                    "type": "MENTIONED_IN",
                    "rule_id": "ner.mention.v1",
                    "confidence": score,
                    "span_start": span_start,
                    "span_end": span_end,
                    "surface_form": surface_form,
                    "evidence": [],
                    "authority": "ner",
                })

    # Build CO_OCCURS_WITH links
    cooccurrence_ner_types = {_LABEL_MAP.get(t, f"ner:{t.lower()}") for t in cooccurrence_types}
    seen_pairs: set[tuple[str, str]] = set()

    for chunk_id, entity_keys in chunk_entity_keys.items():
        # Filter to cooccurrence-eligible types AND drop references to entities
        # that were filtered out by the post-extraction quality filter above.
        eligible = [
            (k, entity_id_map[k])
            for k in entity_keys
            if k[0] in cooccurrence_ner_types and entity_id_map[k] in surviving_entity_ids
        ]
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
