from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from auditgraph.plugins.schema import ExtractorPluginConfig


@dataclass(frozen=True)
class PluginSpec:
    name: str
    module: str
    kind: str
    config: dict[str, Any]


def load_plugins(raw_config: dict[str, Any]) -> list[PluginSpec]:
    plugins = raw_config.get("plugins", [])
    specs: list[PluginSpec] = []
    for entry in plugins:
        if not isinstance(entry, dict):
            continue
        specs.append(
            PluginSpec(
                name=entry.get("name", ""),
                module=entry.get("module", ""),
                kind=entry.get("kind", ""),
                config=entry.get("config", {}),
            )
        )
    return specs


def load_extractor_plugins(raw_config: dict[str, Any]) -> list[ExtractorPluginConfig]:
    extractors = raw_config.get("extractors", [])
    specs: list[ExtractorPluginConfig] = []
    for entry in extractors:
        if not isinstance(entry, dict):
            continue
        specs.append(
            ExtractorPluginConfig(
                name=entry.get("name", ""),
                module=entry.get("module", ""),
                entrypoint=entry.get("entrypoint", ""),
                config=entry.get("config", {}),
            )
        )
    return specs
