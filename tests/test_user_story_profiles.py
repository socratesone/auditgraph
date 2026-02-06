from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.storage.artifacts import profile_pkg_root


def test_us9_profiles_isolate_roots(tmp_path: Path) -> None:
    work_cfg = tmp_path / "work.json"
    work_cfg.write_text(
        '{"active_profile": "work", "profiles": {"work": {}}}',
        encoding="utf-8",
    )
    personal_cfg = tmp_path / "personal.json"
    personal_cfg.write_text(
        '{"active_profile": "personal", "profiles": {"personal": {}}}',
        encoding="utf-8",
    )

    work_root = profile_pkg_root(tmp_path, load_config(work_cfg))
    personal_root = profile_pkg_root(tmp_path, load_config(personal_cfg))

    assert work_root != personal_root
    assert work_root.parts[-1] == "work"
    assert personal_root.parts[-1] == "personal"
