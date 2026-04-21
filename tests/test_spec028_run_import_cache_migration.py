"""Spec-028 regression · run_import must apply FR-016b1 cache-completeness
check just like run_ingest.

Bug: run_import's cache-hit branch skipped the `_markdown_document_is_complete`
check. A pre-028 cached markdown document imported through this path was
marked source_origin="cached" while still missing document.text, then
extract raised FR-016b2.

Fix: apply the same completeness check in run_import's cache-hit branch.
"""
from __future__ import annotations

import json
from pathlib import Path


from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, write_json
from auditgraph.storage.hashing import deterministic_document_id, sha256_file


def _scaffold_import_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Prepare a workspace and a pre-028 cached markdown document whose
    payload is missing the `text` field. Returns (root, target_source_dir).
    """
    root = tmp_path  # run_import's path-policy requires sources under root
    (root / "config").mkdir()
    (root / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [imported]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n",
        encoding="utf-8",
    )
    source_dir = root / "imported"
    source_dir.mkdir()
    md_path = source_dir / "intro.md"
    md_path.write_text("# Intro\n\nUse `Redis`.\n", encoding="utf-8")

    # Stage a pre-028 cached document record for this exact source, WITHOUT text.
    source_hash = sha256_file(md_path)
    document_id = deterministic_document_id(md_path.as_posix(), source_hash)
    config = load_config(root / "config" / "pkg.yaml")
    pkg_root = profile_pkg_root(root, config)
    (pkg_root / "documents").mkdir(parents=True)
    write_json(
        pkg_root / "documents" / f"{document_id}.json",
        {
            "document_id": document_id,
            "source_path": md_path.as_posix(),
            "source_hash": source_hash,
            "mime_type": "text/markdown",
            "file_size": md_path.stat().st_size,
            "extractor_id": "text_plain_parser",
            "extractor_version": "v1",
            "ingest_config_hash": "legacy",
            "status": "ok",
            "status_reason": None,
            "hash_history": [source_hash],
            # NOTE: no `text` field — pre-028 shape.
        },
    )
    return root, source_dir


def test_run_import_refreshes_incomplete_cached_markdown_document(tmp_path: Path) -> None:
    root, source_dir = _scaffold_import_workspace(tmp_path)
    config = load_config(root / "config" / "pkg.yaml")
    runner = PipelineRunner()

    result = runner.run_import(root=root, config=config, targets=[str(source_dir)])
    assert result.status == "ok"

    # Inspect the refreshed document payload — `text` must be present now.
    pkg_root = profile_pkg_root(root, config)
    doc_files = list((pkg_root / "documents").glob("doc_*.json"))
    assert doc_files
    payload = json.loads(doc_files[0].read_text(encoding="utf-8"))
    assert payload.get("text"), (
        "run_import should have refreshed the incomplete pre-028 record via "
        "the cache-migration path (FR-016b1); instead it took the cache-hit "
        "branch and left `text` missing, which would break extract's FR-016b2 guard"
    )

    # Extract MUST now succeed (the text is in place).
    extract_result = runner.run_extract(root=root, config=config)
    assert extract_result.status == "ok"


def test_run_import_post_028_complete_cache_still_takes_normal_cache_path(tmp_path: Path) -> None:
    """Post-028 documents (with text) continue to take the normal cache hit."""
    root, source_dir = _scaffold_import_workspace(tmp_path)
    config = load_config(root / "config" / "pkg.yaml")
    runner = PipelineRunner()
    # Migration run — writes text.
    runner.run_import(root=root, config=config, targets=[str(source_dir)])

    # Second import — normal cache hit.
    result = runner.run_import(root=root, config=config, targets=[str(source_dir)])
    manifest = json.loads(Path(result.detail["manifest"]).read_text(encoding="utf-8"))
    intro = next(r for r in manifest["records"] if r["path"].endswith("intro.md"))
    assert intro["source_origin"] == "cached"
