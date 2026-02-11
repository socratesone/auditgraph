from __future__ import annotations

from typing import Any

from auditgraph.storage.hashing import sha256_text
from auditgraph.utils.redaction import Redactor
from auditgraph.storage.ontology import canonical_key, resolve_type
from auditgraph.storage.audit import DEFAULT_PIPELINE_VERSION


def _entity_id(canonical_key: str) -> str:
    return f"ent_{sha256_text(canonical_key)}"


def build_entity(symbol: dict[str, Any], source_hash: str, redactor: Redactor | None = None) -> dict[str, Any]:
    canonical_key = str(symbol["canonical_key"])
    name = str(symbol["name"])
    if redactor:
        canonical_key = str(redactor.redact_text(canonical_key).value)
        name = str(redactor.redact_text(name).value)
    return {
        "id": _entity_id(canonical_key),
        "type": symbol["type"],
        "name": name,
        "canonical_key": canonical_key,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.code_symbols.v1",
            "input_hash": source_hash,
            "pipeline_version": DEFAULT_PIPELINE_VERSION,
        },
        "refs": [
            {
                "source_path": symbol["source_path"],
                "source_hash": source_hash,
                "range": {"start_line": 1, "end_line": 1},
            }
        ],
    }


def build_note_entity(title: str, source_path: str, source_hash: str, redactor: Redactor | None = None) -> dict[str, Any]:
    redacted_title = title
    if redactor:
        redacted_title = str(redactor.redact_text(title).value)
    canonical = canonical_key(redacted_title)
    entity_type = resolve_type({"type": "note"}, primary="ag", allow_secondary=True)
    return {
        "id": _entity_id(canonical),
        "type": entity_type,
        "name": redacted_title,
        "canonical_key": canonical,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.note.v1",
            "input_hash": source_hash,
            "pipeline_version": DEFAULT_PIPELINE_VERSION,
        },
        "refs": [
            {
                "source_path": source_path,
                "source_hash": source_hash,
                "range": {"start_line": 1, "end_line": 1},
            }
        ],
    }


def build_log_claim(signature: dict[str, Any], redactor: Redactor | None = None) -> dict[str, Any]:
    text = str(signature.get("signature", ""))
    if redactor:
        text = str(redactor.redact_text(text).value)
    claim_id = f"clm_{sha256_text(text)}"
    return {
        "id": claim_id,
        "subject_id": None,
        "type": "error_signature",
        "predicate": "observed",
        "object": {"signature": text},
        "provenance": {
            "source_file": signature.get("source_path", ""),
            "extractor_rule_id": "log.signature.v1",
        },
    }
