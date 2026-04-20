"""End-to-end story test: Dan, the solo engineer.

Story claims being verified (from `stories/solo-engineer-future-self.md`):

  > He pointed auditgraph at his Markdown notes and a few PDFs and ran it
  > locally. Now, when he searched a specific term, he got back stable
  > entities and the exact matching snippets, and he could browse related
  > nodes instead of re-reading entire documents. Nothing felt "generated";
  > it felt indexed, structured, and inspectable.
  >
  > The payoff was psychological as much as practical: when Dan updated a
  > note or added a new doc, re-running produced consistent, diffable
  > outputs.

Each test below maps to a specific clause from the story. If a test
fails, the story claim no longer holds — that's a regression in the
value proposition, not just a unit-level bug.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import (
    assert_postcondition_pass,
    build_workspace,
    find_chunks_containing,
    find_entities_for_term,
    latest_index_manifest,
    pkg_default,
    rebuild,
)


pytestmark = pytest.mark.slow


# Verbatim phrases that should survive ingest unchanged. Tests grep for
# these in the chunk text to prove "exact matching snippets, not generated".
PHRASE_REFRESH_VERIFIED = "OAuth refresh token rotation is the verified root cause"
PHRASE_PROXY_HYPOTHESIS = "we hypothesize that the proxy timeout is responsible"


def _dan_corpus() -> dict[str, str]:
    return {
        "notes/incident-2024-09-12.md": (
            "---\n"
            "title: Incident 2024-09-12 OAuth Outage\n"
            "---\n"
            "\n"
            "# Incident notes\n"
            "\n"
            f"{PHRASE_REFRESH_VERIFIED} based on log review of the auth service.\n"
            "\n"
            f"As a working theory, {PHRASE_PROXY_HYPOTHESIS}, but this is not yet confirmed.\n"
        ),
        "notes/deep-dive-oauth.md": (
            "---\n"
            "title: OAuth Deep Dive\n"
            "---\n"
            "\n"
            "# Deep dive\n"
            "\n"
            "Reference RFC 6749 section 6 on refresh token rotation. The pattern\n"
            "matters because rotated tokens prevent replay attacks.\n"
        ),
        "notes/verified-vs-hypothesis.md": (
            "---\n"
            "title: Verified Versus Hypothesis Tracking\n"
            "---\n"
            "\n"
            "# Tracking what we know\n"
            "\n"
            "Verified facts must cite a log line or repro. Hypotheses must say\n"
            "so explicitly. This note does not mention the OAuth incident directly.\n"
        ),
        "notes/runbook-proxy.md": (
            "---\n"
            "title: Proxy Runbook\n"
            "---\n"
            "\n"
            "# Runbook\n"
            "\n"
            "The proxy timeout default is 60 seconds. Increasing it has not\n"
            "historically resolved auth-flow regressions.\n"
        ),
    }


def test_search_returns_traceable_entities_and_exact_snippets(tmp_path: Path):
    """Story claim: 'searched a specific term, he got back stable entities
    and the exact matching snippets'."""
    workspace = build_workspace(tmp_path, _dan_corpus())
    rebuild(workspace)

    # 1. The redaction postcondition passes — proves the corpus is clean
    #    and the pipeline self-validated.
    assert_postcondition_pass(latest_index_manifest(workspace))

    # 2. Searching for a term from the incident note returns at least one
    #    entity. The token is what BM25 indexes from the title "OAuth Deep
    #    Dive" / "Incident 2024-09-12 OAuth Outage".
    entities = find_entities_for_term(workspace, "oauth")
    assert entities, "BM25 returned no hits for 'oauth' — the index is not built"

    # 3. Every returned entity has full provenance — id, name, and a non-empty
    #    refs list pointing back to a real source file. This is the "stable
    #    entities" + "nothing generated" claim made concrete.
    workspace_files = {f for f in _dan_corpus().keys() if f.endswith(".md")}
    for entity in entities:
        assert entity.get("id"), f"entity missing id: {entity}"
        assert entity.get("name"), f"entity missing name: {entity}"
        refs = entity.get("refs") or []
        assert refs, f"entity {entity['id']} has no refs"
        for ref in refs:
            sp = ref.get("source_path", "")
            assert any(sp.endswith(f) for f in workspace_files), (
                f"entity ref points outside the corpus: {sp}"
            )

    # 4. The exact verbatim phrase from the source file survives into a
    #    retrievable chunk — the "exact matching snippets" half of the claim.
    matching_chunks = find_chunks_containing(workspace, PHRASE_REFRESH_VERIFIED)
    assert matching_chunks, (
        f"verbatim source phrase not found in any chunk: {PHRASE_REFRESH_VERIFIED!r}"
    )
    # The chunk's source_path resolves back to the incident note.
    assert any(
        c.get("source_path", "").endswith("notes/incident-2024-09-12.md")
        for c in matching_chunks
    ), "matching chunk does not trace to the incident note source file"


def test_browse_related_nodes_via_neighbors(tmp_path: Path):
    """Story claim: 'he could browse related nodes instead of re-reading
    entire documents'."""
    from auditgraph.query.neighbors import neighbors

    workspace = build_workspace(tmp_path, _dan_corpus())
    rebuild(workspace)

    # Pick the OAuth Deep Dive note entity (deterministic name).
    entities = find_entities_for_term(workspace, "oauth")
    assert entities
    target = entities[0]

    pkg_root = pkg_default(workspace)
    result = neighbors(pkg_root, str(target["id"]))
    # `neighbors` returns a structured result; the relevant key is the
    # neighbor list (called `neighbors` in the current implementation).
    neighbor_list = result.get("neighbors") if isinstance(result, dict) else None
    assert neighbor_list is not None, f"neighbors result missing 'neighbors' key: {result}"

    # The story claim is "browse related", not "the graph is dense". On a
    # tiny corpus the cooccurrence threshold may produce zero links — what
    # we MUST verify is that the call works and returns the documented
    # shape, so a future regression in the neighbors API breaks this test.
    assert isinstance(neighbor_list, list)


def test_re_running_produces_consistent_diffable_outputs(tmp_path: Path):
    """Story claim: 'when Dan updated a note or added a new doc, re-running
    produced consistent, diffable outputs'.

    Concrete operationalization, given how auditgraph actually models
    documents: ``document_id`` is derived from ``source_path`` only and is
    stable across edits — the document is the file's *identity*, not its
    *version*. Per-edit revisions are tracked by the ``source_hash`` field
    inside each document and by the per-run manifests under ``runs/``.

    So the diffable claim cashes out as:
      1. Every document_id is preserved across runs (stable identifiers
         for external references).
      2. Editing a file changes its source_hash; the unedited files'
         source_hashes are byte-identical across runs (no hidden
         non-determinism).
      3. The run manifests under runs/ accumulate so the operator can
         diff two points in time.
    """
    from auditgraph.storage.loaders import load_documents

    workspace = build_workspace(tmp_path, _dan_corpus())
    rebuild(workspace)
    manifest_a = latest_index_manifest(workspace)
    run_id_a = manifest_a["run_id"]

    pkg_root = pkg_default(workspace)
    docs_run1 = {d["document_id"]: d["source_hash"] for d in load_documents(pkg_root)}
    paths_run1 = {d["document_id"]: d["source_path"] for d in load_documents(pkg_root)}
    assert len(docs_run1) >= 4, f"expected 4+ documents, got {len(docs_run1)}"

    # Edit one file. Append, don't rewrite — minimizes the diff.
    edited = workspace / "notes" / "incident-2024-09-12.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nFollow-up note: rotation is now enforced.\n",
        encoding="utf-8",
    )

    rebuild(workspace)
    manifest_b = latest_index_manifest(workspace)
    assert_postcondition_pass(manifest_b)
    run_id_b = manifest_b["run_id"]

    docs_run2 = {d["document_id"]: d["source_hash"] for d in load_documents(pkg_root)}

    # 1. Stable identifiers across runs
    assert set(docs_run1.keys()) == set(docs_run2.keys()), (
        f"document_ids drifted across runs: {set(docs_run1.keys()) ^ set(docs_run2.keys())}"
    )

    # 2. Find which document changed source_hash
    changed_hash_ids = {
        doc_id
        for doc_id in docs_run1
        if docs_run1[doc_id] != docs_run2[doc_id]
    }
    assert len(changed_hash_ids) == 1, (
        f"expected exactly 1 doc to change source_hash, got {len(changed_hash_ids)}: {changed_hash_ids}"
    )
    changed_id = next(iter(changed_hash_ids))
    assert paths_run1[changed_id].endswith("notes/incident-2024-09-12.md"), (
        f"the doc whose hash changed is not the edited file: {paths_run1[changed_id]}"
    )

    # 3. Run manifests accumulate — diff window between two runs is on disk
    assert run_id_a != run_id_b, "edit produced identical run_id (inputs_hash didn't notice)"
    runs_dir = pkg_root / "runs"
    run_dirs = {p.name for p in runs_dir.iterdir() if p.is_dir()}
    assert run_id_a in run_dirs and run_id_b in run_dirs, (
        f"missing one of the per-run dirs: {run_id_a}, {run_id_b}, found {run_dirs}"
    )
