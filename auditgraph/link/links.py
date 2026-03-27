from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json
from auditgraph.storage.sharding import shard_dir


def write_links(pkg_root: Path, links: Iterable[dict[str, object]]) -> list[Path]:
    paths: list[Path] = []
    for link in links:
        link_id = str(link["id"])
        shard = shard_dir(pkg_root / "links", link_id)
        path = shard / f"{link_id}.json"
        write_json(path, link)
        paths.append(path)
    return paths
