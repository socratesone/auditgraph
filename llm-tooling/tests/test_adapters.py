from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_adapter_bundle_matches_manifest(manifest_path: Path) -> None:
    bundle_path = manifest_path.parent / "adapters" / "openai.functions.json"
    with bundle_path.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)

    manifest = _load_manifest(manifest_path)
    manifest_tools = {tool["name"] for tool in manifest.get("tools", [])}
    adapter_tools = {tool["name"] for tool in bundle.get("tools", [])}

    assert manifest_tools == adapter_tools


def test_adapter_bundle_is_deterministic(manifest_path: Path) -> None:
    generator_path = manifest_path.parent / "generate_adapters.py"
    generator = _load_module(generator_path, "generate_adapters")
    assert hasattr(generator, "generate_adapter_bundle")

    manifest = _load_manifest(manifest_path)
    generated = generator.generate_adapter_bundle(manifest)

    bundle_path = manifest_path.parent / "adapters" / "openai.functions.json"
    with bundle_path.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)

    assert generated == bundle
