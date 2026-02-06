from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.extract.manifest import write_entities
from auditgraph.storage.artifacts import profile_pkg_root


def test_profile_pkg_root_layout(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)

    assert pkg_root == tmp_path / ".pkg" / "profiles" / "default"


def test_entity_shard_uses_suffix(tmp_path: Path) -> None:
    config = load_config(None)
    pkg_root = profile_pkg_root(tmp_path, config)
    entity = {"id": "ent_ab1234", "type": "note", "name": "Note"}

    paths = write_entities(pkg_root, [entity])

    assert paths
    assert paths[0].parent.name == "ab"
