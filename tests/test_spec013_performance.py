from __future__ import annotations

from pathlib import Path

from auditgraph.utils.quality_gates import evaluate_performance_gates


CONFIG_PATH = Path("tests/fixtures/spec013/performance/config.yaml")


def test_performance_gates_pass_within_threshold() -> None:
    metrics = {
        "keyword_p50": 0.04,
        "keyword_p95": 0.19,
        "ingest_extract_100_files": 9.0,
    }

    results = evaluate_performance_gates(CONFIG_PATH, metrics)

    assert all(result.status == "pass" for result in results)


def test_performance_gates_fail_on_regression() -> None:
    metrics = {
        "keyword_p50": 0.04,
        "keyword_p95": 0.30,
        "ingest_extract_100_files": 9.0,
    }

    results = evaluate_performance_gates(CONFIG_PATH, metrics)

    assert any(result.status == "fail" for result in results)
