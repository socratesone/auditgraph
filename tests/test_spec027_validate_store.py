"""Spec 027 User Story 6 — validate-store command (FR-019..FR-022).

Audits an existing `.pkg/profiles/<profile>/` for strings matching the
current redaction detector allowlist. Strictly read-only. See
`specs/027-security-hardening/contracts/cli-commands.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query.validate_store import validate_store
from auditgraph.storage.artifacts import profile_pkg_root


def _build_clean_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "notes").mkdir(parents=True)
    (workspace / "notes" / "clean.md").write_text(
        "# Clean note\n\nThis is a regular note with no secrets.\n", encoding="utf-8"
    )
    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=workspace, config=config)
    assert result.status == "ok"
    return workspace


def _poison_one_chunk(workspace: Path, profile: str = "default") -> Path:
    pkg = workspace / ".pkg" / "profiles" / profile / "chunks"
    chunk_files = sorted(pkg.rglob("*.json"))
    assert chunk_files, f"no chunks under {pkg}"
    target = chunk_files[0]
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["text"] = "password=INJECTED_SENTINEL_DO_NOT_LEAK"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_clean_store_exits_zero(tmp_path: Path):
    workspace = _build_clean_workspace(tmp_path)
    config = load_config(None)
    pkg_root = workspace / ".pkg"
    result = validate_store(pkg_root, config=config, profile=None, all_profiles=False)
    assert result["status"] == "pass", f"unexpected status: {result}"
    assert result["misses"] == []
    assert result.get("profile") == "default"


def test_poisoned_store_exits_nonzero(tmp_path: Path):
    workspace = _build_clean_workspace(tmp_path)
    _poison_one_chunk(workspace)
    config = load_config(None)
    pkg_root = workspace / ".pkg"
    result = validate_store(pkg_root, config=config, profile=None, all_profiles=False)
    assert result["status"] == "fail", f"expected fail, got {result}"
    assert len(result["misses"]) >= 1
    categories = {m["category"] for m in result["misses"]}
    assert "credential" in categories
    # Secret value MUST NOT appear anywhere
    assert "INJECTED_SENTINEL_DO_NOT_LEAK" not in json.dumps(result)


def test_no_pkg_exits_zero_with_message(tmp_path: Path):
    workspace = tmp_path / "empty"
    workspace.mkdir()
    config = load_config(None)
    pkg_root = workspace / ".pkg"
    result = validate_store(pkg_root, config=config, profile=None, all_profiles=False)
    assert result["status"] == "pass"
    assert "message" in result
    assert "no store" in result["message"].lower()


def test_profile_override(tmp_path: Path):
    """Build two profiles; poison only 'dev'; confirm --profile targeting."""
    workspace = _build_clean_workspace(tmp_path)
    # Fabricate a 'dev' profile by copying default under profiles/dev
    import shutil
    dev = workspace / ".pkg" / "profiles" / "dev"
    shutil.copytree(workspace / ".pkg" / "profiles" / "default", dev)
    _poison_one_chunk(workspace, profile="dev")

    config = load_config(None)
    pkg_root = workspace / ".pkg"

    default_result = validate_store(pkg_root, config=config, profile="default", all_profiles=False)
    assert default_result["status"] == "pass", f"default should be clean: {default_result}"

    dev_result = validate_store(pkg_root, config=config, profile="dev", all_profiles=False)
    assert dev_result["status"] == "fail"
    assert dev_result.get("profile") == "dev"


def test_all_profiles_flag(tmp_path: Path):
    workspace = _build_clean_workspace(tmp_path)
    import shutil
    dev = workspace / ".pkg" / "profiles" / "dev"
    shutil.copytree(workspace / ".pkg" / "profiles" / "default", dev)
    _poison_one_chunk(workspace, profile="dev")

    config = load_config(None)
    pkg_root = workspace / ".pkg"
    result = validate_store(pkg_root, config=config, profile=None, all_profiles=True)
    assert "profiles" in result
    assert set(result["profiles"].keys()) >= {"default", "dev"}
    assert result["profiles"]["default"]["status"] == "pass"
    assert result["profiles"]["dev"]["status"] == "fail"
    assert result["poisoned_profiles"] == ["dev"]
    assert result["total_misses"] >= 1


def test_scope_excludes_runs_indexes_secrets(tmp_path: Path):
    """FR-019 / Clarification Q5: scanner walks entities/chunks/segments/documents/sources only."""
    workspace = _build_clean_workspace(tmp_path)
    pkg_root = workspace / ".pkg"
    default_profile = pkg_root / "profiles" / "default"

    # Write credential-shaped content to runs/, indexes/, secrets/
    for subdir in ("runs", "indexes", "secrets"):
        d = default_profile / subdir / "bogus"
        d.mkdir(parents=True, exist_ok=True)
        (d / "poison.json").write_text(
            json.dumps({"text": "password=OUT_OF_SCOPE_SENTINEL"}), encoding="utf-8"
        )

    config = load_config(None)
    result = validate_store(pkg_root, config=config, profile=None, all_profiles=False)
    # These should not be reported as misses
    for miss in result.get("misses", []):
        assert not miss["path"].startswith("runs/"), f"runs/ incorrectly scanned: {miss}"
        assert not miss["path"].startswith("indexes/"), f"indexes/ incorrectly scanned: {miss}"
        assert not miss["path"].startswith("secrets/"), f"secrets/ incorrectly scanned: {miss}"


def test_read_only_contract(tmp_path: Path):
    """FR-022: validate_store MUST NOT mutate any file under .pkg/."""
    workspace = _build_clean_workspace(tmp_path)
    default_profile = workspace / ".pkg" / "profiles" / "default"

    # Record all mtimes before the scan
    before: dict[Path, float] = {}
    for path in default_profile.rglob("*"):
        if path.is_file():
            before[path] = path.stat().st_mtime_ns

    config = load_config(None)
    validate_store(workspace / ".pkg", config=config, profile=None, all_profiles=False)

    for path, mtime in before.items():
        assert path.exists(), f"validate_store deleted {path}"
        assert path.stat().st_mtime_ns == mtime, f"validate_store mutated {path}"
