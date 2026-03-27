"""Tests for duration_ms tracking in pipeline replay log entries."""
from __future__ import annotations

import json
from pathlib import Path

from auditgraph.config import load_config
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.storage.artifacts import read_json


def _setup_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with one markdown note."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    note_path = notes_dir / "note.md"
    note_path.write_text("---\ntitle: Duration Test\n---\nHello world", encoding="utf-8")
    return tmp_path


def _read_replay_lines(pkg_root: Path, run_id: str) -> list[dict]:
    """Read all replay log lines for a given run."""
    replay_path = pkg_root / "runs" / run_id / "replay-log.jsonl"
    assert replay_path.exists(), f"replay log not found at {replay_path}"
    lines = []
    for line in replay_path.read_text(encoding="utf-8").strip().splitlines():
        lines.append(json.loads(line))
    return lines


def _get_replay_for_stage(replay_lines: list[dict], stage: str) -> dict:
    """Get the replay line for a specific stage."""
    for line in replay_lines:
        if line.get("stage") == stage:
            return line
    raise AssertionError(f"No replay line found for stage '{stage}'")


class TestIngestDurationTracking:
    def test_ingest_replay_has_duration_ms(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_ingest(root=root, config=config)
        assert result.status == "ok"

        manifest_path = Path(result.detail["manifest"])
        run_id = manifest_path.parent.name
        pkg_root = manifest_path.parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        ingest_line = _get_replay_for_stage(replay_lines, "ingest")

        assert "duration_ms" in ingest_line
        assert isinstance(ingest_line["duration_ms"], int)
        assert ingest_line["duration_ms"] >= 0

    def test_ingest_replay_has_hash_fields(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_ingest(root=root, config=config)
        assert result.status == "ok"

        manifest_path = Path(result.detail["manifest"])
        run_id = manifest_path.parent.name
        pkg_root = manifest_path.parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        ingest_line = _get_replay_for_stage(replay_lines, "ingest")

        assert "inputs_hash" in ingest_line
        assert "outputs_hash" in ingest_line
        assert len(ingest_line["inputs_hash"]) > 0
        assert len(ingest_line["outputs_hash"]) > 0


class TestNormalizeDurationTracking:
    def test_normalize_replay_has_duration_ms(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        ingest_result = runner.run_ingest(root=root, config=config)
        run_id = Path(ingest_result.detail["manifest"]).parent.name

        result = runner.run_normalize(root=root, config=config, run_id=run_id)
        assert result.status == "ok"

        pkg_root = Path(ingest_result.detail["manifest"]).parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        normalize_line = _get_replay_for_stage(replay_lines, "normalize")

        assert "duration_ms" in normalize_line
        assert isinstance(normalize_line["duration_ms"], int)
        assert normalize_line["duration_ms"] >= 0

    def test_normalize_replay_has_hash_fields(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        ingest_result = runner.run_ingest(root=root, config=config)
        run_id = Path(ingest_result.detail["manifest"]).parent.name

        result = runner.run_normalize(root=root, config=config, run_id=run_id)
        assert result.status == "ok"

        pkg_root = Path(ingest_result.detail["manifest"]).parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        normalize_line = _get_replay_for_stage(replay_lines, "normalize")

        assert "inputs_hash" in normalize_line
        assert "outputs_hash" in normalize_line


class TestExtractDurationTracking:
    def test_extract_replay_has_duration_ms(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        ingest_result = runner.run_ingest(root=root, config=config)
        run_id = Path(ingest_result.detail["manifest"]).parent.name
        runner.run_normalize(root=root, config=config, run_id=run_id)

        result = runner.run_extract(root=root, config=config, run_id=run_id)
        assert result.status == "ok"

        pkg_root = Path(ingest_result.detail["manifest"]).parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        extract_line = _get_replay_for_stage(replay_lines, "extract")

        assert "duration_ms" in extract_line
        assert isinstance(extract_line["duration_ms"], int)
        assert extract_line["duration_ms"] >= 0


class TestLinkDurationTracking:
    def test_link_replay_has_duration_ms(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        ingest_result = runner.run_ingest(root=root, config=config)
        run_id = Path(ingest_result.detail["manifest"]).parent.name
        runner.run_normalize(root=root, config=config, run_id=run_id)
        runner.run_extract(root=root, config=config, run_id=run_id)

        result = runner.run_link(root=root, config=config, run_id=run_id)
        assert result.status == "ok"

        pkg_root = Path(ingest_result.detail["manifest"]).parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        link_line = _get_replay_for_stage(replay_lines, "link")

        assert "duration_ms" in link_line
        assert isinstance(link_line["duration_ms"], int)
        assert link_line["duration_ms"] >= 0


class TestIndexDurationTracking:
    def test_index_replay_has_duration_ms(self, tmp_path: Path) -> None:
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        ingest_result = runner.run_ingest(root=root, config=config)
        run_id = Path(ingest_result.detail["manifest"]).parent.name
        runner.run_normalize(root=root, config=config, run_id=run_id)
        runner.run_extract(root=root, config=config, run_id=run_id)
        runner.run_link(root=root, config=config, run_id=run_id)

        result = runner.run_index(root=root, config=config, run_id=run_id)
        assert result.status == "ok"

        pkg_root = Path(ingest_result.detail["manifest"]).parent.parent.parent
        replay_lines = _read_replay_lines(pkg_root, run_id)
        index_line = _get_replay_for_stage(replay_lines, "index")

        assert "duration_ms" in index_line
        assert isinstance(index_line["duration_ms"], int)
        assert index_line["duration_ms"] >= 0


class TestFullPipelineDurationTracking:
    def test_rebuild_last_stage_has_duration_ms(self, tmp_path: Path) -> None:
        """The last stage written in a full rebuild should have duration_ms.

        Note: write_text overwrites the replay log file, so only the last
        stage's replay line survives after a full rebuild.  We verify that
        the final replay line (index) contains the expected fields.
        """
        root = _setup_workspace(tmp_path)
        runner = PipelineRunner()
        config = load_config(None)
        result = runner.run_rebuild(root=root, config=config)
        assert result.status == "ok"

        run_id = result.detail["run_id"]
        pkg_root = tmp_path / ".pkg" / "profiles" / "default"
        replay_lines = _read_replay_lines(pkg_root, run_id)

        # Only the last stage (index) remains because write_text overwrites
        last_line = replay_lines[-1]
        assert "duration_ms" in last_line, "last stage missing duration_ms"
        assert isinstance(last_line["duration_ms"], int)
        assert last_line["duration_ms"] >= 0
        assert "inputs_hash" in last_line
        assert "outputs_hash" in last_line
