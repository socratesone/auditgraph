"""Spec-028 US4 · Rule-pack validator.

Validates that every path referenced by a profile's ``extraction.rule_packs``
or ``linking.rule_packs`` list resolves to a readable YAML file. Relative
paths are resolved against the WORKSPACE ROOT (the directory containing
``config/pkg.yaml``), NOT the config file's parent — using the config
file's parent would double-resolve ``config/extractors/core.yaml`` against
``<root>/config/`` and produce the nonexistent ``<root>/config/config/…``
(see adjustments2.md §4).

Package-resource fallback: when a workspace-relative path does not exist
on disk, try ``importlib.resources.files("auditgraph") / "_package_data" /
<path>``. This lets shipped wheels supply the stubs even in workspaces
where the user deleted or never copied them.
"""
from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class RulePackError(Exception):
    """Structured error raised when a rule-pack path fails validation."""

    kind: str  # "missing" | "malformed"
    path: str
    reason: str

    def __str__(self) -> str:  # pragma: no cover — formatting only
        if self.kind == "missing":
            return f"rule pack missing: {self.path} (reason: {self.reason})"
        if self.kind == "malformed":
            return f"rule pack malformed: {self.path} (reason: {self.reason})"
        return f"rule pack error: {self.path}"


def _resolve_candidate(declared: str, workspace_root: Path) -> Path | None:
    """Return the first resolvable path for ``declared`` or None.

    Resolution order:
      1. Absolute path → used verbatim (no fallback).
      2. Relative path → try ``workspace_root / declared`` on disk.
      3. Package-resource fallback: ``auditgraph/_package_data/<declared>``.
    """
    declared_path = Path(declared)
    if declared_path.is_absolute():
        return declared_path if declared_path.is_file() else None

    workspace_candidate = workspace_root / declared_path
    if workspace_candidate.is_file():
        return workspace_candidate

    # Package-resource fallback via importlib.resources.
    try:
        resource = importlib.resources.files("auditgraph") / "_package_data" / str(declared_path)
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    try:
        if resource.is_file():  # type: ignore[attr-defined]
            # Materialize to a Path; importlib.resources returns a Traversable.
            # read_bytes() works for validation; to resolve, use as_file context.
            with importlib.resources.as_file(resource) as real_path:
                return real_path
    except (FileNotFoundError, AttributeError):
        pass
    return None


def validate_rule_pack_paths(
    paths: Iterable[str],
    workspace_root: Path,
) -> None:
    """Validate every path resolves to a readable, parseable YAML file.

    Raises
    ------
    RulePackError(kind="missing")
        If a path resolves to neither the workspace nor a package resource.
    RulePackError(kind="malformed")
        If a resolved file exists but yaml.safe_load raises.
    """
    for declared in paths or []:
        resolved = _resolve_candidate(str(declared), workspace_root)
        if resolved is None:
            raise RulePackError(
                kind="missing",
                path=str(declared),
                reason="not found in workspace or shipped package resources",
            )
        try:
            with resolved.open("r", encoding="utf-8") as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise RulePackError(
                kind="malformed",
                path=str(declared),
                reason=f"yaml.safe_load failed: {exc}",
            ) from exc
        except OSError as exc:  # pragma: no cover — defensive only
            raise RulePackError(
                kind="missing",
                path=str(declared),
                reason=f"could not read resolved path: {exc}",
            ) from exc
