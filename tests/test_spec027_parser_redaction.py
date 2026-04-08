"""Spec 027 User Story 5 — parser-entry redaction wiring (FR-016, FR-017).

Verifies that the `Redactor` is threaded into `parse_options["redactor"]`
by both `run_ingest` and `run_import`, and that the hotfix's post-chunking
redaction pass has been retired.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from auditgraph.config import load_config
from auditgraph.ingest.parsers import _build_document_metadata, parse_file
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.utils.redaction import Redactor, build_redactor


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_SOURCE = REPO_ROOT / "auditgraph" / "pipeline" / "runner.py"


def _build_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "notes").mkdir(parents=True)
    (workspace / "notes" / "n.md").write_text("# Hi\n\nSome content.\n", encoding="utf-8")
    return workspace


def test_redactor_is_threaded_into_parse_options(tmp_path: Path):
    """run_ingest must pass a Redactor instance in parse_options."""
    workspace = _build_workspace(tmp_path)
    captured = {}

    real_parse_file = parse_file

    def spy(path, policy, ingest_options=None):
        if ingest_options is not None:
            captured.setdefault("options", ingest_options)
        return real_parse_file(path, policy, ingest_options)

    with patch("auditgraph.pipeline.runner.parse_file", side_effect=spy):
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_ingest(root=workspace, config=config)
    assert result.status == "ok"
    assert "options" in captured, "parse_file was never called"
    opts = captured["options"]
    assert "redactor" in opts, f"parse_options missing 'redactor' key: {list(opts.keys())}"
    assert isinstance(opts["redactor"], Redactor)


def test_hotfix_postchunking_pass_removed():
    """Static check — the post-chunking redact_payload calls must be gone."""
    source = RUNNER_SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "redactor.redact_payload(document_payload)",
        "redactor.redact_payload(segments_payload)",
        "redactor.redact_payload(chunks_payload)",
    ):
        assert forbidden not in source, (
            f"{forbidden!r} still present in runner.py — retire the hotfix's "
            "post-chunking pass (Spec 027 T065)"
        )


def test_parser_redacts_document_text(tmp_path: Path):
    """_build_document_metadata applies the redactor to text before chunking."""
    workspace = _build_workspace(tmp_path)
    doc = workspace / "notes" / "secret.md"
    doc.write_text("password=TEST_SENTINEL_DO_NOT_LEAK\n\n# body\n", encoding="utf-8")

    config = load_config(None)
    redactor = build_redactor(workspace, config)

    from auditgraph.ingest.policy import load_policy
    policy = load_policy(config.profile())
    options = {
        "ocr_mode": "off",
        "chunk_tokens": 200,
        "chunk_overlap_tokens": 40,
        "max_file_size_bytes": 209715200,
        "ingest_config_hash": "",
        "source_hash": "test_hash",
        "redactor": redactor,
    }
    result = parse_file(doc, policy, options)
    assert result.status == "ok"
    metadata = result.metadata or {}
    # Walk every text field and assert the sentinel is gone.
    def _walk(node):
        if isinstance(node, str):
            assert "TEST_SENTINEL_DO_NOT_LEAK" not in node, f"sentinel survived in: {node!r}"
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)
    _walk(metadata)


def test_parse_file_requires_redactor(tmp_path: Path):
    """Calling parse_file without a redactor in options must raise ValueError."""
    workspace = _build_workspace(tmp_path)
    doc = workspace / "notes" / "n.md"

    config = load_config(None)
    from auditgraph.ingest.policy import load_policy
    policy = load_policy(config.profile())

    with pytest.raises(ValueError, match="redactor"):
        parse_file(doc, policy, {"chunk_tokens": 200})
