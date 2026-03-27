from __future__ import annotations

from pathlib import Path


def shard_dir(root: Path, identifier: str) -> Path:
    """Return the two-character shard subdirectory for a given identifier."""
    token = identifier.split("_", 1)[-1]
    shard = token[:2] if token else identifier[:2]
    return root / shard
