from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.config import load_config
from auditgraph.extract.entities import build_entity
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import sha256_text


def pkg_root(root: Path) -> Path:
    return profile_pkg_root(root, load_config(None))


def make_entity(name: str, source_path: str) -> dict[str, object]:
    source_hash = sha256_text(f"{name}:{source_path}")
    return build_entity(
        {
            "type": "file",
            "name": name,
            "canonical_key": f"file:{source_path}",
            "source_path": source_path,
        },
        source_hash,
    )


def assert_no_secret_in_dir(base_dir: Path, secret: str, *, allowlist: Iterable[Path] | None = None) -> None:
    allowset = {path.resolve() for path in (allowlist or [])}
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() in allowset:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert secret not in content, f"Found secret in {path}"
