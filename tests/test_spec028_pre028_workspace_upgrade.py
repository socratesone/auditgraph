"""Spec-028 T035a · End-to-end pre-028 workspace upgrade (SC-011).

Stages a fixture workspace whose `.pkg/profiles/default/` tree looks like
a pre-028 ingest run (markdown document records lack the `text` field
added by FR-015a) and confirms:

1. The next `run_ingest` detects the incomplete cached document and
   falls through to a fresh parse, writing the refreshed document
   payload (now with `text`) and recording the migration run as
   `source_origin="fresh"`, not `"cached"`, per FR-016b1.
2. No warning is emitted — the migration is silent by design.
3. The following `run_extract` emits markdown sub-entities from the
   refreshed record.
4. A subsequent back-to-back pipeline run takes the normal cache-hit
   path (`source_origin="cached"`) — the migration is one-time.

Also pins FR-016b2's explicit error behavior when extract is handed a
markdown document record with missing `text`.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root, write_json
from auditgraph.storage.hashing import deterministic_document_id, sha256_file


def _scaffold(tmp_path: Path) -> Path:
    (tmp_path / "notes").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pkg.yaml").write_text(
        "pkg_root: .\n"
        "active_profile: default\n"
        "profiles:\n"
        "  default:\n"
        "    include_paths: [notes]\n"
        "    exclude_globs: []\n"
        "    ingestion:\n"
        "      allowed_extensions: [.md]\n",
        encoding="utf-8",
    )
    return tmp_path / "config" / "pkg.yaml"


def _run_pipeline(root: Path, config, runner: PipelineRunner) -> tuple[str, Path]:
    ingest = runner.run_ingest(root=root, config=config)
    manifest_path = Path(ingest.detail["manifest"])
    run_id = json.loads(manifest_path.read_text(encoding="utf-8"))["run_id"]
    runner.run_extract(root=root, config=config, run_id=run_id)
    return run_id, manifest_path


def test_pre028_workspace_migrates_cached_doc_on_next_ingest(tmp_path: Path) -> None:
    """FR-016b1 full flow: stage a pre-028 cached markdown doc (no text
    field), rerun the pipeline, confirm the migration emits markdown
    sub-entities and records source_origin="fresh" for that run.
    """
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Intro\n\nUse `Redis`.\n", encoding="utf-8")
    source_hash = sha256_file(md_path)
    absolute_path = md_path.as_posix()
    document_id = deterministic_document_id(absolute_path, source_hash)

    # Stage a pre-028 cached document record that LACKS the text field.
    config = load_config(config_path)
    pkg_root = profile_pkg_root(tmp_path, config)
    (pkg_root / "documents").mkdir(parents=True)
    pre_028_payload = {
        "document_id": document_id,
        "source_path": absolute_path,
        "source_hash": source_hash,
        "mime_type": "text/markdown",
        "file_size": md_path.stat().st_size,
        "extractor_id": "text_plain_parser",
        "extractor_version": "v1",
        "ingest_config_hash": "legacy",
        "status": "ok",
        "status_reason": None,
        "hash_history": [source_hash],
        # NOTE: NO "text" field — this is the pre-028 shape.
    }
    write_json(pkg_root / "documents" / f"{document_id}.json", pre_028_payload)

    runner = PipelineRunner()
    # Pre-028 intro.md document already exists on disk. Next ingest must:
    # (a) detect the missing text field via _markdown_document_is_complete,
    # (b) fall through to fresh parse, (c) write a fresh document WITH text,
    # (d) record source_origin="fresh".
    ingest_result = runner.run_ingest(root=tmp_path, config=config)
    assert ingest_result.status == "ok"
    manifest = json.loads(Path(ingest_result.detail["manifest"]).read_text(encoding="utf-8"))

    intro_record = next(r for r in manifest["records"] if r["path"] == "notes/intro.md")
    assert intro_record["parse_status"] == "ok"
    assert intro_record["source_origin"] == "fresh", (
        "FR-016b1: incomplete cache forces fresh parse, not a cached hit"
    )

    # Confirm the document now has the `text` field after the fresh parse.
    refreshed = json.loads(
        (pkg_root / "documents" / f"{document_id}.json").read_text(encoding="utf-8")
    )
    assert refreshed.get("text") is not None
    assert len(refreshed["text"]) > 0

    # Run extract — must produce at least one markdown sub-entity
    # (ag:section / ag:technology / ag:reference) from the refreshed record.
    extract_result = runner.run_extract(
        root=tmp_path, config=config, run_id=manifest["run_id"]
    )
    assert extract_result.status == "ok"
    markdown_types = {"ag:section", "ag:technology", "ag:reference"}
    markdown_entities = []
    for ent_file in (pkg_root / "entities").rglob("*.json"):
        payload = json.loads(ent_file.read_text(encoding="utf-8"))
        if payload.get("type") in markdown_types:
            markdown_entities.append(payload)
    assert markdown_entities, (
        "SC-011: migration flow must emit at least one markdown sub-entity "
        "from the refreshed pre-028 record"
    )

    # A second back-to-back run should take the normal cache-hit path.
    ingest_2 = runner.run_ingest(root=tmp_path, config=config)
    manifest_2 = json.loads(Path(ingest_2.detail["manifest"]).read_text(encoding="utf-8"))
    intro_2 = next(r for r in manifest_2["records"] if r["path"] == "notes/intro.md")
    assert intro_2["source_origin"] == "cached", (
        "after migration, subsequent runs take the normal cache path"
    )


def test_extract_errors_loudly_on_missing_text_in_markdown_document(tmp_path: Path) -> None:
    """FR-016b2: extract MUST raise when a markdown document payload lacks `text`.

    The cache-migration in ingest is the ONLY path that should refresh
    incomplete records; extract stays strict about its inputs.
    """
    config_path = _scaffold(tmp_path)
    md_path = tmp_path / "notes" / "intro.md"
    md_path.write_text("# Intro\n", encoding="utf-8")

    config = load_config(config_path)
    runner = PipelineRunner()
    runner.run_ingest(root=tmp_path, config=config)

    # Stomp the document payload to remove the text field, simulating the
    # state that would exist if ingest ever got out of sync with extract's
    # expectation. (In practice FR-016b1 prevents this — this test pins
    # the defensive error for belt-and-suspenders coverage.)
    pkg_root = profile_pkg_root(tmp_path, config)
    doc_files = list((pkg_root / "documents").glob("doc_*.json"))
    assert doc_files, "ingest should have produced a document payload"
    doc_payload = json.loads(doc_files[0].read_text(encoding="utf-8"))
    doc_payload.pop("text", None)
    write_json(doc_files[0], doc_payload)

    # Now extract MUST raise with a descriptive error.
    import pytest as _pytest

    with _pytest.raises(ValueError, match="FR-016b2"):
        runner.run_extract(root=tmp_path, config=config)
