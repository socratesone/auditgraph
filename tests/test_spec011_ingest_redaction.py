from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from tests.support import assert_no_secret_in_dir


SENTINEL = "S011_SECRET_SENTINEL"


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
