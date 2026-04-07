from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from tests.support import assert_no_secret_in_dir


SENTINEL = "S011_SECRET_SENTINEL"
BODY_SENTINEL = "S026_BODY_SENTINEL"


def test_ingest_redacts_frontmatter_before_persist(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    fixture = Path(__file__).parent / "fixtures" / "spec011" / "secret_note.md"
    (notes_dir / "secret_note.md").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)

    assert result.status == "ok"
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    assert_no_secret_in_dir(pkg_root / "sources", SENTINEL)


def _write_body_sentinel_note(notes_dir: Path) -> None:
    """Create a note whose BODY contains a credential-shaped sentinel.

    The detector `credential_kv` targets `(password|secret|token|api_key|
    apikey|client_secret|private_key)\\s*[:=]\\s*<value>`. By embedding
    `password=S026_BODY_SENTINEL` in the body prose we force the sentinel
    into the chunk text path. Before the Spec 026 C1 fix, that sentinel
    would persist verbatim in `chunks/*.json` because only `sources/`
    was routed through the redactor. After the fix, it must be scrubbed
    from every shard.
    """
    notes_dir.mkdir(parents=True, exist_ok=True)
    body = (
        "# Incident report\n\n"
        "During the triage the following credential was rotated:\n\n"
        f"    password={BODY_SENTINEL}\n\n"
        "The rotation was verified end-to-end. This note is intentionally\n"
        "designed so that the sentinel appears only inside a credential-\n"
        "shaped key=value expression, which the redactor must catch.\n"
    )
    (notes_dir / "body_secret.md").write_text(body, encoding="utf-8")


def test_ingest_redacts_body_credentials_across_all_shards(tmp_path: Path) -> None:
    """SECURITY regression for Spec 026 finding C1.

    Previously only `sources/<hash>.json` was routed through the
    redactor. Document bodies carrying credential-shaped strings ended
    up in cleartext inside `chunks/`, `segments/`, and `documents/`
    shards. This test asserts the sentinel is absent from every
    persisted artifact under `.pkg/profiles/default/` — not just the
    sources directory.
    """
    _write_body_sentinel_note(tmp_path / "notes")

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_ingest(root=tmp_path, config=config)
    assert result.status == "ok"

    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    # Walk every persisted shard, not just sources/. Before the C1 fix
    # this assertion would fail on the chunks/ shard.
    for shard in ("sources", "documents", "segments", "chunks"):
        shard_dir = pkg_root / shard
        if shard_dir.exists():
            assert_no_secret_in_dir(shard_dir, BODY_SENTINEL)


def test_import_redacts_body_credentials_across_all_shards(tmp_path: Path) -> None:
    """SECURITY regression for Spec 026 finding C1 — `run_import` path.

    `auditgraph import <path>` has the same bug class as `auditgraph
    ingest`: it calls `write_json` (not `write_json_redacted`) for
    every artifact it writes. Before the C1 fix, `run_import` wrote
    credentials in cleartext to BOTH `sources/` and `chunks/` —
    strictly worse than `run_ingest`, which at least redacted
    `sources/`. This test covers both.
    """
    notes_dir = tmp_path / "imported_notes"
    _write_body_sentinel_note(notes_dir)

    runner = PipelineRunner()
    config = load_config(None)
    result = runner.run_import(
        root=tmp_path,
        config=config,
        targets=[str(notes_dir)],
    )
    assert result.status == "ok"

    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    for shard in ("sources", "documents", "segments", "chunks"):
        shard_dir = pkg_root / shard
        if shard_dir.exists():
            assert_no_secret_in_dir(shard_dir, BODY_SENTINEL)
