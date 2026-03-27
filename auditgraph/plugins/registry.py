from __future__ import annotations

from typing import Any

from auditgraph.plugins.schema import ExtractorPluginConfig


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
