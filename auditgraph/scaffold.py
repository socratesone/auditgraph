from __future__ import annotations

import importlib.resources
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

# Spec-028 FR-021 / adjustments2.md §8: `auditgraph init` copies the
# shipped rule-pack stubs into the workspace so the default pkg.yaml
# never references orphan paths. Source is the `auditgraph/_package_data`
# subpackage via importlib.resources (works in both wheel-installed and
# editable-installed environments).
_PACKAGE_STUB_TARGETS = (
    ("_package_data/config/extractors/core.yaml", "config/extractors/core.yaml"),
    ("_package_data/config/link_rules/core.yaml", "config/link_rules/core.yaml"),
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

    # Copy the shipped rule-pack stubs. Idempotent — existing files are
    # not overwritten (users can customize their local copies).
    for package_relative, workspace_relative in _PACKAGE_STUB_TARGETS:
        target = root / workspace_relative
        if target.exists():
            continue
        try:
            resource = importlib.resources.files("auditgraph") / package_relative
            text = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        created.append(str(target))

    return created
