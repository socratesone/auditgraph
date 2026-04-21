"""Spec-028 US4 · Rule-pack validator tests.

Exercises FR-021/FR-022/FR-023 + the path-resolution rule from adjustments2 §4
(relative paths resolve against `workspace_root`, NOT the config file's parent).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from auditgraph.utils.rule_packs import RulePackError, validate_rule_pack_paths


def test_default_rule_packs_validate_from_workspace(tmp_path: Path) -> None:
    """The shipped stubs live at `<workspace_root>/config/...` after init."""
    (tmp_path / "config" / "extractors").mkdir(parents=True)
    (tmp_path / "config" / "extractors" / "core.yaml").write_text(
        "version: v1\nextractors: []\n", encoding="utf-8"
    )
    (tmp_path / "config" / "link_rules").mkdir(parents=True)
    (tmp_path / "config" / "link_rules" / "core.yaml").write_text(
        "version: v1\nlink_rules: []\n", encoding="utf-8"
    )

    # Both default paths validate against the workspace.
    validate_rule_pack_paths(
        ["config/extractors/core.yaml", "config/link_rules/core.yaml"],
        tmp_path,
    )


def test_default_rule_packs_validate_via_package_resource_fallback(tmp_path: Path) -> None:
    """Workspace-local paths absent → validator falls back to package resources."""
    # No local config/ directory at all — only shipped stubs.
    validate_rule_pack_paths(
        ["config/extractors/core.yaml", "config/link_rules/core.yaml"],
        tmp_path,
    )


def test_missing_path_raises_rule_pack_error_missing(tmp_path: Path) -> None:
    with pytest.raises(RulePackError) as exc_info:
        validate_rule_pack_paths(["config/does-not-exist.yaml"], tmp_path)
    assert exc_info.value.kind == "missing"


def test_malformed_yaml_raises_rule_pack_error_malformed(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text(
        "not: valid\n  : yaml here\nindent: :broken\n [ unclosed", encoding="utf-8"
    )
    with pytest.raises(RulePackError) as exc_info:
        validate_rule_pack_paths(["bad.yaml"], tmp_path)
    assert exc_info.value.kind == "malformed"


def test_absolute_path_resolves_verbatim(tmp_path: Path) -> None:
    abs_path = tmp_path / "abs.yaml"
    abs_path.write_text("version: v1\n", encoding="utf-8")
    # Absolute path should be used as-is, not rejoined with workspace_root.
    validate_rule_pack_paths([str(abs_path)], tmp_path)


def test_empty_list_is_valid(tmp_path: Path) -> None:
    validate_rule_pack_paths([], tmp_path)


def test_relative_path_resolves_against_workspace_root(tmp_path: Path) -> None:
    """No path doubling (adjustments2.md §4).

    pkg.yaml at <workspace_root>/config/pkg.yaml with rule_packs: ['config/x.yaml']
    MUST resolve to <workspace_root>/config/x.yaml, NOT <workspace_root>/config/config/x.yaml.
    """
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "x.yaml").write_text("version: v1\n", encoding="utf-8")
    # The workspace_root argument MUST be the directory containing config/,
    # not config/ itself. Validator resolves "config/x.yaml" against it.
    validate_rule_pack_paths(["config/x.yaml"], tmp_path)


def test_error_kind_distinguishes_missing_vs_malformed(tmp_path: Path) -> None:
    # Missing
    with pytest.raises(RulePackError) as e_miss:
        validate_rule_pack_paths(["ghost.yaml"], tmp_path)
    assert e_miss.value.kind == "missing"

    # Malformed
    bad = tmp_path / "bad.yaml"
    bad.write_text("[broken unclosed", encoding="utf-8")
    with pytest.raises(RulePackError) as e_mal:
        validate_rule_pack_paths(["bad.yaml"], tmp_path)
    assert e_mal.value.kind == "malformed"

    assert e_miss.value.kind != e_mal.value.kind
