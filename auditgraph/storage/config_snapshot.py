from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.storage.artifacts import write_json
from auditgraph.storage.hashing import sha256_text


def _sanitize_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(payload)
    security = sanitized.get("security")
    if isinstance(security, dict):
        redaction = security.get("redaction")
        if isinstance(redaction, dict):
            for key in ("key", "key_path", "secret", "secret_key", "key_material"):
                redaction.pop(key, None)
    for key in ("redaction_key", "secret", "secret_key"):
        sanitized.pop(key, None)
    return sanitized


def write_config_snapshot(pkg_root: Path, run_id: str, config: Config) -> tuple[Path, str]:
    payload: dict[str, Any] = _sanitize_snapshot(config.raw)
    serialized = json.dumps(payload, sort_keys=True)
    config_hash = sha256_text(serialized)
    path = pkg_root / "runs" / run_id / "config-snapshot.json"
    write_json(path, payload)
    return path, config_hash
