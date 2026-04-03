"""Tests for CLI workspace auto-discovery (_resolve_root and _resolve_config)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


class TestResolveRoot:
    """Tests for _resolve_root fallback chain: --root > AUDITGRAPH_ROOT > CWD."""

    def test_explicit_arg_returns_that_path(self, tmp_path: Path) -> None:
        from auditgraph.cli import _resolve_root

        target = tmp_path / "explicit"
        target.mkdir()
        result = _resolve_root(str(target))
        assert result == target.resolve()

    def test_env_var_overrides_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_root

        env_root = tmp_path / "env_workspace"
        env_root.mkdir()
        monkeypatch.setenv("AUDITGRAPH_ROOT", str(env_root))
        result = _resolve_root(None)
        assert result == env_root.resolve()

    def test_cwd_with_pkg_dir_returns_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_root

        (tmp_path / ".pkg").mkdir()
        monkeypatch.delenv("AUDITGRAPH_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = _resolve_root(None)
        assert result == tmp_path.resolve()

    def test_no_indicators_returns_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_root

        monkeypatch.delenv("AUDITGRAPH_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = _resolve_root(None)
        assert result == tmp_path.resolve()

    def test_dot_arg_falls_through_to_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_root

        env_root = tmp_path / "env_workspace"
        env_root.mkdir()
        monkeypatch.setenv("AUDITGRAPH_ROOT", str(env_root))
        result = _resolve_root(".")
        assert result == env_root.resolve()


class TestResolveConfig:
    """Tests for _resolve_config fallback chain: --config > AUDITGRAPH_CONFIG > <root>/config/pkg.yaml."""

    def test_explicit_arg_returns_that_path(self, tmp_path: Path) -> None:
        from auditgraph.cli import _resolve_config

        cfg = tmp_path / "custom.yaml"
        cfg.touch()
        result = _resolve_config(str(cfg), tmp_path)
        assert result == cfg.resolve()

    def test_env_var_overrides_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_config

        env_cfg = tmp_path / "env_config.yaml"
        env_cfg.touch()
        monkeypatch.setenv("AUDITGRAPH_CONFIG", str(env_cfg))
        result = _resolve_config(None, tmp_path)
        assert result == env_cfg.resolve()

    def test_finds_default_config_when_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_config

        monkeypatch.delenv("AUDITGRAPH_CONFIG", raising=False)
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        cfg_file = cfg_dir / "pkg.yaml"
        cfg_file.touch()
        result = _resolve_config(None, tmp_path)
        assert result == cfg_file

    def test_returns_none_when_nothing_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from auditgraph.cli import _resolve_config

        monkeypatch.delenv("AUDITGRAPH_CONFIG", raising=False)
        result = _resolve_config(None, tmp_path)
        assert result is None
