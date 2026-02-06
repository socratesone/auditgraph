from __future__ import annotations

import unicodedata


def normalize_text(text: str, unicode_form: str = "NFC", line_endings: str = "LF") -> str:
    normalized = unicodedata.normalize(unicode_form, text)
    if line_endings.upper() == "LF":
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return normalized
