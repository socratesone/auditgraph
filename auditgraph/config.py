from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditgraph.utils.profile import validate_profile_name


DEFAULT_PROFILE_NAME = "default"

DEFAULT_CONFIG: dict[str, Any] = {
    "pkg_root": ".",
    "active_profile": DEFAULT_PROFILE_NAME,
    "run_metadata": {"pipeline_version": "v0.1.0"},
    "security": {
        "redaction": {
            "enabled": True,
            "policy_id": "redaction.policy.v1",
            "policy_version": "v1",
            "detectors": [
                "pem_private_key",
                "jwt",
                "bearer_token",
                "credential_kv",
                "url_credentials",
                "vendor_token",
            ],
        }
    },
    "profiles": {
        DEFAULT_PROFILE_NAME: {
            "include_paths": ["notes", "repos"],
            "exclude_globs": ["**/node_modules/**", "**/.git/**"],
            "ingestion": {
                "allowed_extensions": [
                    ".md",
                    ".markdown",
                    ".txt",
                    ".log",
                    ".py",
                    ".js",
                    ".ts",
                    ".tsx",
                    ".jsx",
                ]
            },
            "normalization": {"unicode": "NFC", "line_endings": "LF", "path_style": "posix"},
            "extraction": {"rule_packs": ["config/extractors/core.yaml"], "llm": {"enabled": False}},
            "linking": {"rule_packs": ["config/link_rules/core.yaml"]},
            "search": {
                "keyword": {"enabled": True},
                "semantic": {"enabled": False},
                "ranking": {"w_kw": 1.0, "w_sem": 0.3, "w_graph": 0.1, "score_rounding": 0.000001},
            },
        }
    },
}


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]
    source_path: Path

    def profile(self, name: str | None = None) -> dict[str, Any]:
        profiles = self.raw.get("profiles", {})
        resolved = name or self.active_profile()
        if resolved in profiles:
            return profiles[resolved]
        if DEFAULT_PROFILE_NAME in profiles:
            return profiles[DEFAULT_PROFILE_NAME]
        return {}

    def active_profile(self) -> str:
        return validate_profile_name(str(self.raw.get("active_profile", DEFAULT_PROFILE_NAME)))


class ConfigError(RuntimeError):
    pass


def redaction_settings(config: Config) -> dict[str, Any]:
    defaults = deepcopy(DEFAULT_CONFIG.get("security", {}).get("redaction", {}))
    security = config.raw.get("security", {})
    if not isinstance(security, dict):
        return defaults
    redaction = security.get("redaction", {})
    if not isinstance(redaction, dict):
        return defaults
    merged = {**defaults, **redaction}
    if "detectors" not in redaction:
        merged["detectors"] = defaults.get("detectors", [])
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ConfigError(
            "YAML configuration requires PyYAML. Install it or provide a JSON config file."
        ) from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config(raw=DEFAULT_CONFIG, source_path=Path("<defaults>"))

    if not path.exists():
        return Config(raw=DEFAULT_CONFIG, source_path=path)

    if path.suffix.lower() in {".json"}:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Config(raw=raw, source_path=path)

    raw = _load_yaml(path)
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping")
    return Config(raw=raw, source_path=path)
