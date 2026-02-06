from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json


def write_decision_index(pkg_root: Path, decisions: Iterable[dict[str, object]]) -> Path:
    index_path = pkg_root / "indexes" / "decisions" / "index.json"
    write_json(index_path, {"decisions": list(decisions)})
    return index_path
