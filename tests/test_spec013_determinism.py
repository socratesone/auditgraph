from __future__ import annotations

from pathlib import Path

from auditgraph.utils.quality_gates import prepare_determinism_run, run_determinism_gate


CONFIG_PATH = Path("tests/fixtures/spec013/determinism/config.yaml")


def test_determinism_gate_passes_for_fixture(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs"
    prepare_determinism_run(CONFIG_PATH, run_dir)

    results = run_determinism_gate(CONFIG_PATH, run_dir)

    assert results[0].status == "pass"


def test_determinism_gate_fails_on_ordering_mismatch(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs"
    prepare_determinism_run(CONFIG_PATH, run_dir)

    ordering_path = run_dir / "ordering.json"
    ordering_path.write_text('{"ids": ["b", "a"]}', encoding="utf-8")

    results = run_determinism_gate(CONFIG_PATH, run_dir)

    assert results[0].status == "fail"
