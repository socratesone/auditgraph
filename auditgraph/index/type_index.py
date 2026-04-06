"""Per-type entity and link index builders."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def sanitize_type_name(type_name: str) -> str:
    """Replace non-alphanumeric characters with underscores."""
    return re.sub(r"[^a-zA-Z0-9]", "_", type_name)


def build_type_indexes(pkg_root: Path, entities: Iterable[dict[str, object]]) -> dict[str, Path]:
    """Build per-type entity index files.

    Writes: indexes/types/<sanitized_type>.json (one per type)
    Each file: sorted JSON array of entity IDs for that type.
    Returns: mapping of type_name -> written file path.
    """
    by_type: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        entity_type = str(entity.get("type", ""))
        entity_id = str(entity.get("id", ""))
        if entity_type and entity_id:
            by_type[entity_type].append(entity_id)

    out_dir = pkg_root / "indexes" / "types"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    for type_name, ids in sorted(by_type.items()):
        ids.sort()
        filename = f"{sanitize_type_name(type_name)}.json"
        path = out_dir / filename
        path.write_text(json.dumps(ids, indent=None))
        result[type_name] = path

    return result


def build_link_type_indexes(pkg_root: Path) -> dict[str, Path]:
    """Build per-type link index files.

    Reads all link files via rglob.
    Writes: indexes/link-types/<sanitized_type>.json
    Returns: mapping of link_type -> written file path.
    """
    links_dir = pkg_root / "links"
    by_type: dict[str, list[str]] = defaultdict(list)

    if links_dir.exists():
        for path in links_dir.rglob("*.json"):
            data = json.loads(path.read_text())
            link_type = str(data.get("type", ""))
            link_id = str(data.get("id", ""))
            if link_type and link_id:
                by_type[link_type].append(link_id)

    out_dir = pkg_root / "indexes" / "link-types"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    for type_name, ids in sorted(by_type.items()):
        ids.sort()
        filename = f"{sanitize_type_name(type_name)}.json"
        path = out_dir / filename
        path.write_text(json.dumps(ids, indent=None))
        result[type_name] = path

    return result
