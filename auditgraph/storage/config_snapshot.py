from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.storage.artifacts import write_json
from auditgraph.storage.hashing import sha256_text


def write_config_snapshot(pkg_root: Path, run_id: str, config: Config) -> tuple[Path, str]:
    payload: dict[str, Any] = config.raw
    serialized = json.dumps(payload, sort_keys=True)
    config_hash = sha256_text(serialized)
    path = pkg_root / "runs" / run_id / "config-snapshot.json"
    write_json(path, payload)
    return path, config_hash
