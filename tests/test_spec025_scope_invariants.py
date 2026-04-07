"""Tests for Spec 025: scope-narrowing invariants.

These tests act as guard-rails for the scope decision: auditgraph does not
extract code symbols, does not gate code chunking on a config flag, and does
not route code files to a `text/code` parser_id. The tests grep the runtime
codebase and assert that the relevant strings are absent.

The tests also verify that file entity IDs are stable across the spec 025
creator change (extract_code_symbols → build_file_nodes), and that a workspace
containing only Python files in include_paths produces zero entities (the
honest outcome of the scope decision).
"""
from __future__ import annotations

import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.storage.hashing import entity_id


# ---------------------------------------------------------------------------
# Helper: grep the runtime codebase
# ---------------------------------------------------------------------------


def _runtime_grep(needle: str) -> list[str]:
    """Grep for `needle` in auditgraph/**/*.py and return matching lines.

    Excludes test files (which may legitimately reference these strings as
    historical data) and bytecode caches.
    """
    result = subprocess.run(
        [
            "grep", "-rn",
            "--include=*.py",
            "--exclude-dir=__pycache__",
            needle,
            "auditgraph/",
        ],
        capture_output=True,
        text=True,
    )
    # grep returns 1 when no matches; that's fine for this test
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# T024 — no code_symbols runtime references
# ---------------------------------------------------------------------------


def test_no_code_symbols_runtime_references_remain():
    """The string `code_symbols` must not appear in any runtime .py file under
    auditgraph/. Test files and historical comments in CLAUDE.md / spec docs
    are exempt because they're not loaded at runtime."""
    matches = _runtime_grep("code_symbols")
    assert matches == [], (
        f"Found runtime references to `code_symbols` after Spec 025 removal:\n"
        + "\n".join(f"  {m}" for m in matches)
        + "\n\nThe extract_code_symbols module and its imports/call sites must "
        f"be deleted entirely per Spec 025 FR-010 and FR-011."
    )


# ---------------------------------------------------------------------------
# T025 — no chunk_code_enabled runtime references
# ---------------------------------------------------------------------------


def test_no_chunk_code_enabled_runtime_references_remain():
    """The chunk_code_enabled config option was added during the quality
    sweep and removed by Spec 025 alongside extract_code_symbols. No runtime
    code should reference it."""
    matches = _runtime_grep("chunk_code_enabled")
    assert matches == [], (
        f"Found runtime references to `chunk_code_enabled` after Spec 025 "
        f"removal:\n" + "\n".join(f"  {m}" for m in matches)
        + "\n\nThe option's plumbing in auditgraph/pipeline/runner.py and "
        f"auditgraph/ingest/parsers.py must be removed per Spec 025 FR-013 "
        f"and FR-014."
    )


# ---------------------------------------------------------------------------
# T026 — no text/code parser_id remains
# ---------------------------------------------------------------------------


def test_no_text_code_parser_id_remains():
    """The `text/code` parser_id constant routed code files through a
    dedicated branch in parse_file. After Spec 025, no code files are
    ingested at all, so the parser_id is dead and must be removed."""
    matches = _runtime_grep("text/code")
    assert matches == [], (
        f"Found runtime references to `text/code` after Spec 025 removal:\n"
        + "\n".join(f"  {m}" for m in matches)
        + "\n\nThe text/code entries in PARSER_BY_SUFFIX and the corresponding "
        f"branch in parse_file must be removed per Spec 025 FR-012 and FR-013."
    )


# ---------------------------------------------------------------------------
# T051 — file entity ID stability across creator change (US4)
# ---------------------------------------------------------------------------


def test_file_entity_id_stable_across_creator_change():
    """Per Spec 025 clarification Q1 and FR-003, the file entity ID is
    derived via entity_id(f"file:{path}") via the same hashing function
    that git provenance's build_links() uses for modifies link to_id values.

    This test pins the exact hash for a known path so that any future
    refactor that accidentally changes the hashing function (or the
    canonical key format) is caught immediately. The hash was verified
    empirically during the spec 025 verification phase.
    """
    expected = "ent_88ad6fe45b1981eb07360e184cafe8ce0c130808a7cb0cff41509edd7228c4f6"
    actual = entity_id("file:auditgraph/extract/ner.py")
    assert actual == expected, (
        f"file entity ID for 'file:auditgraph/extract/ner.py' has changed.\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        f"This breaks backwards compatibility with existing workspaces that "
        f"contain file entities. The hashing function or canonical key format "
        f"must not change without a spec-level migration plan."
    )


# ---------------------------------------------------------------------------
# T052 — workspace with only Python in include_paths produces no entities (US4)
# ---------------------------------------------------------------------------


def test_workspace_with_only_python_in_include_paths_produces_no_entities(tmp_path):
    """After Spec 025, source code files are not ingested. A workspace
    containing only `.py` files in its include_paths should produce zero
    entities. This is the honest outcome of the scope decision: code files
    are skipped at the ingest stage with `unsupported_extension`.
    """
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "foo.py").write_text("x = 1\n")

    raw = deepcopy(DEFAULT_CONFIG)
    raw["profiles"]["default"]["include_paths"] = ["notes"]
    raw["profiles"]["default"]["exclude_globs"] = []
    config = Config(raw=raw, source_path=tmp_path / "pkg.yaml")

    runner = PipelineRunner()
    ingest_result = runner.run_ingest(root=tmp_path, config=config, enforce_compatibility=False)
    assert ingest_result.status == "ok", f"ingest failed: {ingest_result.detail}"

    manifest_path = Path(str(ingest_result.detail["manifest"]))
    run_id = manifest_path.parent.name

    # Run normalize and extract — these should run cleanly even with no
    # ingestible files
    normalize_result = runner.run_normalize(root=tmp_path, config=config, run_id=run_id)
    assert normalize_result.status == "ok", f"normalize failed: {normalize_result.detail}"

    extract_result = runner.run_extract(root=tmp_path, config=config, run_id=run_id)
    assert extract_result.status == "ok", f"extract failed: {extract_result.detail}"

    # The entity store should be empty (no entities for the .py file because
    # .py is no longer in allowed_extensions)
    pkg_root = profile_pkg_root(tmp_path, config)
    entities_dir = pkg_root / "entities"
    if entities_dir.exists():
        entity_files = list(entities_dir.rglob("*.json"))
    else:
        entity_files = []

    assert entity_files == [], (
        f"Expected zero entities for a workspace containing only .py files, "
        f"but found {len(entity_files)}:\n"
        + "\n".join(f"  {f}" for f in entity_files[:5])
    )
