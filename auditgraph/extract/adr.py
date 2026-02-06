from __future__ import annotations

from pathlib import Path

from auditgraph.storage.hashing import sha256_text


def extract_decisions(path: Path) -> list[dict[str, object]]:
    if "adr" not in path.name.lower():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    title = text.splitlines()[0] if text else path.name
    decision = {
        "decision": title.lstrip("# ").strip() or path.name,
        "context": "",
        "consequences": [],
    }
    claim_text = f"decision:{decision['decision']}"
    claim_id = f"clm_{sha256_text(claim_text)}"
    return [
        {
            "id": claim_id,
            "type": "decision",
            "predicate": "decided",
            "object": decision,
            "provenance": {
                "source_file": path.as_posix(),
                "extractor_rule_id": "md.adr.v1",
            },
        }
    ]
