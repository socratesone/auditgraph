"""Pipeline performance baseline tests."""
from __future__ import annotations

import time
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner


def _create_docs(root: Path, count: int) -> None:
    """Create a workspace with the given number of markdown documents."""
    notes = root / "notes"
    notes.mkdir(parents=True)
    for i in range(count):
        (notes / f"doc_{i:03d}.md").write_text(
            f"# Document {i}\n\n"
            f"This document covers topic {i} with some technical content.\n"
            f"It references component_{i} and service_{i} in the architecture.\n",
            encoding="utf-8",
        )


def test_pipeline_10_docs_under_5s(tmp_path: Path) -> None:
    """Full pipeline on 10 documents completes in under 5 seconds."""
    _create_docs(tmp_path, 10)

    runner = PipelineRunner()
    config = load_config(None)

    start = time.monotonic()
    result = runner.run_stage("rebuild", root=tmp_path, config=config)
    elapsed = time.monotonic() - start

    assert result.status == "ok"
    assert elapsed < 5.0, f"Pipeline took {elapsed:.2f}s, expected < 5s"


def test_pipeline_scales_sublinearly(tmp_path: Path) -> None:
    """Pipeline time does not grow faster than linearly with document count."""
    small_root = tmp_path / "small"
    large_root = tmp_path / "large"
    _create_docs(small_root, 5)
    _create_docs(large_root, 20)

    runner = PipelineRunner()
    config = load_config(None)

    start = time.monotonic()
    runner.run_stage("rebuild", root=small_root, config=config)
    small_time = time.monotonic() - start

    start = time.monotonic()
    runner.run_stage("rebuild", root=large_root, config=config)
    large_time = time.monotonic() - start

    # 4x more docs should not take more than 6x the time
    ratio = large_time / max(small_time, 0.001)
    assert ratio < 6.0, f"Scaling ratio {ratio:.1f}x for 4x docs, expected < 6x"
