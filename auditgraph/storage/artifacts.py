from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def profile_pkg_root(root: Path, config: Config) -> Path:
    profile = config.active_profile()
    return root / ".pkg" / "profiles" / profile
