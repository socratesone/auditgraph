from __future__ import annotations

from auditgraph.normalize.text import normalize_text


def normalize_document_text(text: str) -> str:
    normalized = normalize_text(text, unicode_form="NFC", line_endings="LF")
    lines = [line.rstrip() for line in normalized.split("\n")]
    collapsed = "\n".join(lines)
    while "\n\n\n" in collapsed:
        collapsed = collapsed.replace("\n\n\n", "\n\n")
    return collapsed.strip()
