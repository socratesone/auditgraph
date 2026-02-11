from __future__ import annotations

from pathlib import Path

from auditgraph.utils.quality_gates import load_test_matrix, run_matrix_gate, validate_test_matrix


FIXTURE_MATRIX = Path("tests/fixtures/spec013/test-matrix.json")


def test_matrix_validation_passes_for_fixture() -> None:
    matrix = load_test_matrix(FIXTURE_MATRIX)

    assert validate_test_matrix(matrix) == []


def test_matrix_gate_fails_on_missing_stage(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(
        '{"stages": [{"stage": "ingest", "unit_tests": ["a"], "integration_tests": ["b"]}]}',
        encoding="utf-8",
    )

    results = run_matrix_gate(matrix_path)

    assert results[0].status == "fail"
