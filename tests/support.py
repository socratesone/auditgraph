from __future__ import annotations

from pathlib import Path
from typing import Iterable
import hashlib
import json

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


def spec017_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "documents"


def ensure_spec017_fixtures() -> dict[str, str]:
    fixture_dir = spec017_fixture_dir()
    manifest_path = fixture_dir / "manifest.json"
    if not manifest_path.exists():
        from tests.fixtures.documents.generate_fixtures import generate

        return generate()
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def assert_spec017_fixture_checksums() -> dict[str, str]:
    expected = ensure_spec017_fixtures()
    fixture_dir = spec017_fixture_dir()
    observed: dict[str, str] = {}
    for name, checksum in expected.items():
        path = fixture_dir / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        observed[name] = digest
        assert digest == checksum
    return observed
