from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.errors import ConfigError


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ConfigError("YAML configuration requires PyYAML.") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def load_jobs_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    if path.suffix.lower() in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))
    return _load_yaml(path)


def resolve_jobs_path(root: Path, config: Config) -> Path:
    return root / "config" / "jobs.yaml"
