from __future__ import annotations

from typing import Any

from auditgraph.storage.hashing import sha256_text


def _entity_id(canonical_key: str) -> str:
    return f"ent_{sha256_text(canonical_key)}"


def build_entity(symbol: dict[str, Any], source_hash: str) -> dict[str, Any]:
    canonical_key = symbol["canonical_key"]
    return {
        "id": _entity_id(canonical_key),
        "type": symbol["type"],
        "name": symbol["name"],
        "canonical_key": canonical_key,
        "aliases": [],
        "provenance": {
            "created_by_rule": "extract.code_symbols.v1",
            "input_hash": source_hash,
            "pipeline_version": "v0.1.0",
        },
        "refs": [
            {
                "source_path": symbol["source_path"],
                "source_hash": source_hash,
                "range": {"start_line": 1, "end_line": 1},
            }
        ],
    }


def build_log_claim(signature: dict[str, Any]) -> dict[str, Any]:
    text = str(signature.get("signature", ""))
    claim_id = f"clm_{sha256_text(text)}"
    return {
        "id": claim_id,
        "type": "error_signature",
        "predicate": "observed",
        "object": {"signature": text},
        "provenance": {
            "source_file": signature.get("source_path", ""),
            "extractor_rule_id": "log.signature.v1",
        },
    }
