"""End-to-end story test: Marta, the regulated team that has to "prove it
under scrutiny".

Story claims being verified (from `stories/regulatory-audit-heavy-team.md`):

  > They adopted auditgraph as a local-first pipeline that produces auditable
  > artifacts: manifests for each run, stable IDs for entities, and explainable
  > links that can be traced back to source material. When an auditor asked
  > where a control requirement was justified, Marta could point to the exact
  > source chunk and show how it flowed into the derived graph, rather than
  > pasting screenshots into a slide deck.
  >
  > And when they needed to share the shape of the evidence, they exported a
  > subgraph (or synced to Neo4j as an optional target) without making Neo4j
  > the source of truth. The team's story became consistent: plain-text
  > sources stay primary, derived artifacts are reproducible, and "where did
  > this come from?" always has a crisp, inspectable answer.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.conftest import (
    assert_postcondition_pass,
    build_workspace,
    find_chunks_containing,
    latest_index_manifest,
    pkg_default,
    rebuild,
)


pytestmark = pytest.mark.slow


CONTROL_MFA = "Control requirement: MFA must be enforced for all production access."
CONTROL_RETENTION = "Control requirement: audit logs are retained for ninety days."


def _marta_corpus() -> dict[str, str]:
    return {
        "notes/policies/access-control.md": (
            "---\n"
            "title: Access Control Policy\n"
            "---\n"
            "\n"
            "# Access control\n"
            "\n"
            f"{CONTROL_MFA}\n"
            "\n"
            "Production access is defined as any session that can write to the\n"
            "primary database or invoke the deploy pipeline.\n"
        ),
        "notes/policies/data-retention.md": (
            "---\n"
            "title: Data Retention Policy\n"
            "---\n"
            "\n"
            "# Retention\n"
            "\n"
            f"{CONTROL_RETENTION} The retention is enforced by the log shipper\n"
            "configuration.\n"
        ),
        "notes/evidence/q3-pen-test-summary.md": (
            "---\n"
            "title: Q3 Pen Test Summary\n"
            "---\n"
            "\n"
            "# Pen test summary\n"
            "\n"
            "The pen test confirmed compliance with access control policy. MFA\n"
            "must be enforced for all production access — this control was\n"
            "tested via attempted bypass and the bypass failed.\n"
        ),
        "notes/evidence/q3-mfa-rollout-status.md": (
            "---\n"
            "title: MFA Rollout Status\n"
            "---\n"
            "\n"
            "# Status\n"
            "\n"
            "MFA is enforced for production access in 100% of identity provider\n"
            "groups as of the Q3 cutover.\n"
        ),
        "notes/audits/2024-soc2-prep-notes.md": (
            "---\n"
            "title: 2024 SOC2 Prep Notes\n"
            "---\n"
            "\n"
            "# Mapping\n"
            "\n"
            "Access control policy maps to SOC2 CC6.1. Evidence: pen test summary\n"
            "and MFA rollout status.\n"
        ),
    }


def test_rebuild_writes_audit_grade_manifest(tmp_path: Path):
    """Story claim: 'manifests for each run … stable IDs for entities'."""
    workspace = build_workspace(tmp_path, _marta_corpus())
    rebuild(workspace)

    manifest = latest_index_manifest(workspace)
    # Audit-grade manifest fields the story implicitly requires
    for required_field in (
        "run_id",
        "inputs_hash",
        "outputs_hash",
        "config_hash",
        "started_at",
        "finished_at",
        "artifacts",
        "redaction_postcondition",  # Spec 027 US8
    ):
        assert required_field in manifest, (
            f"manifest missing audit field {required_field!r}: keys={list(manifest.keys())}"
        )
    assert_postcondition_pass(manifest)


def test_auditor_can_trace_claim_back_to_source_chunk(tmp_path: Path):
    """Story claim: 'When an auditor asked where a control requirement was
    justified, Marta could point to the exact source chunk'."""
    workspace = build_workspace(tmp_path, _marta_corpus())
    rebuild(workspace)

    # An auditor asks: "Where is the MFA control requirement defined?"
    # Marta runs a query for the verbatim phrase and gets back a chunk
    # whose source_path resolves to the access control policy file.
    chunks = find_chunks_containing(workspace, CONTROL_MFA)
    assert chunks, f"verbatim control requirement phrase not found: {CONTROL_MFA!r}"

    # Every returned chunk has the audit fields needed to make a defensible
    # claim: chunk_id, document_id, source_path, source_hash. The auditor
    # can verify the source_hash matches the file on disk if they want to.
    for chunk in chunks:
        assert chunk.get("chunk_id"), f"chunk missing chunk_id: {chunk}"
        assert chunk.get("document_id"), f"chunk missing document_id: {chunk}"
        assert chunk.get("source_path"), f"chunk missing source_path: {chunk}"
        assert chunk.get("source_hash"), f"chunk missing source_hash: {chunk}"

    # At least one matching chunk traces to the policy file (not the
    # pen test summary, which paraphrases but isn't the source of truth).
    sources = {c.get("source_path", "") for c in chunks}
    assert any(s.endswith("notes/policies/access-control.md") for s in sources), (
        f"control requirement chunk does not trace to access-control policy: {sources}"
    )


def test_export_subgraph_to_workspace_relative_path(tmp_path: Path):
    """Story claim: 'when they needed to share the shape of the evidence,
    they exported a subgraph … without making Neo4j the source of truth'."""
    from auditgraph.config import load_config
    from auditgraph.export.json import export_json
    from auditgraph.storage.artifacts import profile_pkg_root

    workspace = build_workspace(tmp_path, _marta_corpus())
    rebuild(workspace)

    config = load_config(None)
    pkg_root = profile_pkg_root(workspace, config)
    output_path = workspace / "exports" / "subgraphs" / "audit-bundle.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result_path = export_json(workspace, pkg_root, output_path, config=config)
    assert result_path.exists(), f"export did not create {result_path}"

    bundle = json.loads(result_path.read_text(encoding="utf-8"))
    # The "shape of the evidence" from Marta's story is realized as the
    # full set of derived shards: entities (the nodes the team queries),
    # documents (the audit anchors), and chunks (the verbatim source
    # snippets that justify each entity). The current JSON export schema
    # serializes these as top-level keys; relationships are implicit in
    # entity↔chunk references rather than a separate `links` array. The
    # value-prop assertion is that an auditor receives a SELF-CONTAINED
    # bundle they can navigate offline.
    for required in ("entities", "documents", "chunks", "export_metadata"):
        assert required in bundle, (
            f"export missing audit field {required!r}: keys={list(bundle.keys())}"
        )
    assert isinstance(bundle["entities"], list) and bundle["entities"], (
        "export entities list is empty — auditor has nothing to inspect"
    )
    assert isinstance(bundle["chunks"], list) and bundle["chunks"], (
        "export chunks list is empty — auditor cannot trace claims to source"
    )
    # Every chunk in the bundle has source provenance — the auditor can
    # resolve any quoted snippet back to a source file without re-running
    # the pipeline.
    for chunk in bundle["chunks"]:
        assert chunk.get("source_path"), f"exported chunk missing source_path: {chunk}"
        assert chunk.get("source_hash"), f"exported chunk missing source_hash: {chunk}"


def test_unchanged_corpus_produces_byte_identical_outputs(tmp_path: Path):
    """Story claim: 'plain-text sources stay primary, derived artifacts are
    reproducible'."""
    workspace = build_workspace(tmp_path, _marta_corpus())

    rebuild(workspace)
    manifest_a = latest_index_manifest(workspace)
    outputs_a = manifest_a["outputs_hash"]

    rebuild(workspace)
    manifest_b = latest_index_manifest(workspace)
    assert manifest_b["outputs_hash"] == outputs_a, (
        "outputs_hash drifted across identical re-runs — Marta cannot defend reproducibility"
    )


def test_corpus_edit_produces_diffable_audit_trail(tmp_path: Path):
    """Story claim: when policies change, the audit trail must show what
    changed and when. Concretely: editing a policy file produces a NEW
    run_id with a DIFFERENT outputs_hash, and BOTH runs remain readable
    side-by-side under runs/."""
    workspace = build_workspace(tmp_path, _marta_corpus())

    rebuild(workspace)
    manifest_a = latest_index_manifest(workspace)
    run_id_a = manifest_a["run_id"]

    # Operator updates the access control policy.
    policy = workspace / "notes" / "policies" / "access-control.md"
    policy.write_text(
        policy.read_text(encoding="utf-8") + "\nUpdated for the 2025 review cycle.\n",
        encoding="utf-8",
    )

    rebuild(workspace)
    manifest_b = latest_index_manifest(workspace)
    run_id_b = manifest_b["run_id"]

    # `run_id = sha256(ingest.inputs_hash + config_hash)`. The ingest stage's
    # inputs_hash is `sha256(sorted source_hashes)`, so a body edit that
    # changes one file's bytes propagates into a different run_id even
    # though downstream stage manifests (link, index) fingerprint by
    # entity/link IDs and don't directly track body content.
    assert run_id_a != run_id_b, "edit produced identical run_id — content not hashed"

    # Both runs are still readable side-by-side under runs/. Marta can
    # show an auditor both states of the policy graph and diff them.
    runs_dir = pkg_default(workspace) / "runs"
    run_dirs = {p.name for p in runs_dir.iterdir() if p.is_dir()}
    assert run_id_a in run_dirs, f"prior run {run_id_a} disappeared after edit"
    assert run_id_b in run_dirs, f"new run {run_id_b} not present"

    # And the ingest-stage outputs_hash for the two runs differs — that's
    # the deepest, most direct proof of source-bytes change propagation.
    import json as _json
    ingest_a = _json.loads((runs_dir / run_id_a / "ingest-manifest.json").read_text(encoding="utf-8"))
    ingest_b = _json.loads((runs_dir / run_id_b / "ingest-manifest.json").read_text(encoding="utf-8"))
    assert ingest_a["outputs_hash"] != ingest_b["outputs_hash"], (
        "ingest outputs_hash unchanged after edit — source_hash didn't propagate"
    )
