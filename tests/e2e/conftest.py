"""Shared fixture builders for the end-to-end story tests.

Each story test in `tests/e2e/test_story_*.py` uses these helpers to keep
its own body focused on the assertions that map back to its story claims.
The helpers themselves are intentionally thin — they wrap the real CLI
entry points (no test doubles, no mock subprocesses), so a regression in
the pipeline surfaces as a story-test failure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner, StageResult
from auditgraph.query.keyword import keyword_search
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.loaders import load_chunks, load_entity


def build_workspace(tmp_path: Path, files: dict[str, str]) -> Path:
    """Materialize ``files`` (relative-path → content) under tmp_path/workspace."""
    workspace = tmp_path / "workspace"
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace


def rebuild(workspace: Path, *, allow_redaction_misses: bool = False) -> StageResult:
    """Run the full pipeline and assert the rebuild stage completed cleanly."""
    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_stage(
        "rebuild",
        root=workspace,
        config=config,
        allow_redaction_misses=allow_redaction_misses,
    )
    assert result.status == "ok", f"rebuild failed: {result.detail}"
    return result


def pkg_default(workspace: Path) -> Path:
    """Return the default-profile pkg_root for ``workspace``."""
    return workspace / ".pkg" / "profiles" / "default"


def latest_index_manifest(workspace: Path) -> dict[str, Any]:
    """Load the most recently-written ``index-manifest.json`` for the
    default profile.

    NOTE: ``run_id`` is a content hash, so sorting manifests alphabetically
    by path returns an arbitrary run, NOT the latest one. We sort by mtime
    instead so an edit-and-rebuild test sees the run it just produced.
    """
    runs_dir = pkg_default(workspace) / "runs"
    assert runs_dir.exists(), f"no runs directory under {pkg_default(workspace)}"
    manifests = list(runs_dir.rglob("index-manifest.json"))
    assert manifests, f"no index-manifest.json under {runs_dir}"
    manifests.sort(key=lambda p: p.stat().st_mtime_ns)
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def assert_postcondition_pass(manifest: dict[str, Any]) -> None:
    """The Spec 027 redaction postcondition must report `pass` on a clean corpus."""
    pc = manifest.get("redaction_postcondition")
    assert pc is not None, "manifest missing redaction_postcondition (Spec 027 US8)"
    assert pc["status"] == "pass", f"postcondition not pass: {pc}"


def find_entities_for_term(workspace: Path, term: str) -> list[dict[str, Any]]:
    """Search BM25 for ``term`` and resolve every hit to its full entity dict.

    BM25 indexes entity names + tokens of names. This helper hides the
    keyword_search → load_entity round-trip so individual tests stay readable.
    """
    pkg_root = pkg_default(workspace)
    hits = keyword_search(pkg_root, term)
    entities: list[dict[str, Any]] = []
    for hit in hits:
        try:
            entities.append(load_entity(pkg_root, str(hit["id"])))
        except Exception:
            # An entity referenced by the index is missing — that's a real
            # bug we'd want to know about, so re-raise rather than swallow.
            raise
    return entities


def find_chunks_containing(workspace: Path, snippet: str) -> list[dict[str, Any]]:
    """Walk every chunk and return the ones whose ``text`` contains ``snippet``.

    Used by tests that need to verify "the verbatim source phrase appears in
    a retrievable chunk", which is a stronger claim than "the BM25 index
    has the term".
    """
    pkg_root = pkg_default(workspace)
    chunks = list(load_chunks(pkg_root))
    return [c for c in chunks if snippet in str(c.get("text", ""))]
