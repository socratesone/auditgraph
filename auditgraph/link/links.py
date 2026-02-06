from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json


def _shard_dir(root: Path, identifier: str) -> Path:
    token = identifier.split("_", 1)[-1]
    shard = token[:2] if token else identifier[:2]
    return root / shard


def write_links(pkg_root: Path, links: Iterable[dict[str, object]]) -> list[Path]:
    paths: list[Path] = []
    for link in links:
        link_id = str(link["id"])
        shard = _shard_dir(pkg_root / "links", link_id)
        path = shard / f"{link_id}.json"
        write_json(path, link)
        paths.append(path)
    return paths
