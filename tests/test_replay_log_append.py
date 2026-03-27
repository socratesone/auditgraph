"""Tests for replay log append behavior across a full rebuild."""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner


def _setup_workspace(tmp_path: Path) -> Path:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "note.md").write_text(
        "---\ntitle: Replay Test\n---\nHello world", encoding="utf-8"
    )
    return tmp_path


def _read_replay_lines(pkg_root: Path, run_id: str) -> list[dict]:
    replay_path = pkg_root / "runs" / run_id / "replay-log.jsonl"
    assert replay_path.exists(), f"replay log not found at {replay_path}"
    lines = []
    for line in replay_path.read_text(encoding="utf-8").strip().splitlines():
        lines.append(json.loads(line))
    return lines


ALL_STAGES = {"ingest", "normalize", "extract", "link", "index"}


class TestReplayLogAppend:
    def test_rebuild_replay_contains_all_stages(self, tmp_path: Path) -> None:
        """After a full rebuild, the replay log must contain entries for ALL stages."""
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_rebuild(root=root, config=config)
        assert result.status == "ok"

        run_id = result.detail["run_id"]
        pkg_root = tmp_path / ".pkg" / "profiles" / "default"
        replay_lines = _read_replay_lines(pkg_root, run_id)

        stages_found = {line["stage"] for line in replay_lines}
        assert stages_found == ALL_STAGES, (
            f"Expected all stages {ALL_STAGES}, found {stages_found}"
        )

    def test_rebuild_replay_has_correct_line_count(self, tmp_path: Path) -> None:
        """After a full rebuild, there should be exactly 5 replay log lines."""
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_rebuild(root=root, config=config)
        assert result.status == "ok"

        run_id = result.detail["run_id"]
        pkg_root = tmp_path / ".pkg" / "profiles" / "default"
        replay_lines = _read_replay_lines(pkg_root, run_id)

        assert len(replay_lines) == 5, (
            f"Expected 5 replay lines, got {len(replay_lines)}"
        )

    def test_rebuild_replay_stages_in_order(self, tmp_path: Path) -> None:
        """Stages should appear in pipeline execution order."""
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_rebuild(root=root, config=config)
        assert result.status == "ok"

        run_id = result.detail["run_id"]
        pkg_root = tmp_path / ".pkg" / "profiles" / "default"
        replay_lines = _read_replay_lines(pkg_root, run_id)

        stage_order = [line["stage"] for line in replay_lines]
        assert stage_order == ["ingest", "normalize", "extract", "link", "index"]
