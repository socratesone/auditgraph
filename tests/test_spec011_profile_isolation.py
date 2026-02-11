from __future__ import annotations

from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.errors import SecurityPolicyError
from auditgraph.storage.artifacts import profile_pkg_root


def test_invalid_active_profile_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"active_profile": "../evil"}', encoding="utf-8")
    config = load_config(config_path)

    with pytest.raises(SecurityPolicyError):
        profile_pkg_root(tmp_path, config)
