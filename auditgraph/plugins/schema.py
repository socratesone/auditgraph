from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractorPluginConfig:
    name: str
    module: str
    entrypoint: str
    config: dict[str, Any]
