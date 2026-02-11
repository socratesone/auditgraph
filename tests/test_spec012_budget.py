from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from auditgraph.config import Config, DEFAULT_CONFIG
from auditgraph.errors import BudgetError
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.utils.budget import evaluate_budget


def test_budget_status_warn_and_block() -> None:
    settings = {"multiplier": 1.0, "warn_threshold": 0.8, "block_threshold": 1.0}
    source_bytes = 1024 * 1024

    warn_status = evaluate_budget(source_bytes, artifact_bytes=900_000, settings=settings, additional_bytes=0)
    assert warn_status.status == "warn"

    block_status = evaluate_budget(source_bytes, artifact_bytes=1_200_000, settings=settings, additional_bytes=0)
    assert block_status.status == "block"


def test_ingest_blocks_when_budget_exceeded(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    large_payload = "a" * (1024 * 1024 + 1)
    (notes_dir / "note.md").write_text(large_payload, encoding="utf-8")

    config = Config(raw=deepcopy(DEFAULT_CONFIG), source_path=tmp_path / "config.json")
    config.raw["storage"]["footprint_budget"] = {
        "multiplier": 1.0,
        "warn_threshold": 0.8,
        "block_threshold": 1.0,
    }

    runner = PipelineRunner()

    with pytest.raises(BudgetError):
        runner.run_ingest(root=tmp_path, config=config)
