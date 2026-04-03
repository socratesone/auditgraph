"""Git provenance configuration loader.

Loads git_provenance settings from the profile dict, applying defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GitProvenanceConfig:
    """Typed configuration for the git provenance stage."""

    enabled: bool = False
    max_tier2_commits: int = 1000
    hot_paths: list[str] = field(default_factory=list)
    cold_paths: list[str] = field(default_factory=lambda: ["*.lock", "*-lock.json", "*.generated.*"])


def load_git_provenance_config(profile: dict[str, Any]) -> GitProvenanceConfig:
    """Load GitProvenanceConfig from a profile dict.

    Args:
        profile: The profile dict (e.g. config.profile()).

    Returns:
        GitProvenanceConfig with values from the profile, falling back to defaults.
    """
    gp = profile.get("git_provenance", {})
    if not isinstance(gp, dict):
        return GitProvenanceConfig()

    return GitProvenanceConfig(
        enabled=bool(gp.get("enabled", False)),
        max_tier2_commits=int(gp.get("max_tier2_commits", 1000)),
        hot_paths=list(gp.get("hot_paths", [])),
        cold_paths=list(gp.get("cold_paths", ["*.lock", "*-lock.json", "*.generated.*"])),
    )
