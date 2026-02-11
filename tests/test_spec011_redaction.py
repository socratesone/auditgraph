from __future__ import annotations

import re
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.utils.redaction import build_redactor


SENTINEL = "S011_SECRET_SENTINEL"


def test_redaction_masks_credential_values(tmp_path: Path) -> None:
    redactor = build_redactor(tmp_path, load_config(None))

    result = redactor.redact_text(f"token={SENTINEL}")

    assert SENTINEL not in result.value
    assert "<<redacted:credential:" in result.value


def test_redaction_is_deterministic_within_profile(tmp_path: Path) -> None:
    redactor = build_redactor(tmp_path, load_config(None))

    result = redactor.redact_text(f"token={SENTINEL} token={SENTINEL}")
    markers = re.findall(r"<<redacted:credential:[0-9a-f]{12}>>", str(result.value))

    assert markers
    assert len(set(markers)) == 1
