from __future__ import annotations

from pathlib import Path

DEFAULT_DIRECTORIES = (
    ".pkg",
    "notes",
    "repos",
    "inbox",
    "exports/reports",
    "config/extractors",
    "config/link_rules",
    "config/profiles",
)


def initialize_workspace(root: Path, config_source: Path) -> list[str]:
    created: list[str] = []
    for relative in DEFAULT_DIRECTORIES:
        target = root / relative
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))

    config_target = root / "config" / "pkg.yaml"
    if not config_target.exists() and config_source.exists():
        config_target.write_text(config_source.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(str(config_target))
    return created
