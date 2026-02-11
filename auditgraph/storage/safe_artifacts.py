from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.storage.artifacts import ensure_dir
from auditgraph.utils.redaction import RedactionResult, Redactor


def write_json_redacted(path: Path, payload: Any, redactor: Redactor) -> RedactionResult:
    result = redactor.redact_payload(payload)
    ensure_dir(path.parent)
    path.write_text(json.dumps(result.value, indent=2, sort_keys=True), encoding="utf-8")
    return result


def write_text_redacted(path: Path, text: str, redactor: Redactor) -> RedactionResult:
    result = redactor.redact_text(text)
    ensure_dir(path.parent)
    path.write_text(str(result.value), encoding="utf-8")
    return result
