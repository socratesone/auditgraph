from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_STAGES = ("ingest", "extract", "link", "index", "query")


@dataclass(frozen=True)
class GateResult:
    status: str
    stage: str
    threshold: float | None
    observed: float | None
    message: str


def _load_json_or_yaml(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ValueError("YAML parsing requires PyYAML") from exc
        payload = yaml.safe_load(content)
        return payload or {}


def load_test_matrix(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_or_yaml(path)
    stages = payload.get("stages", [])
    if not isinstance(stages, list):
        return []
    return [item for item in stages if isinstance(item, dict)]


def validate_test_matrix(matrix: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    stages_present = {str(item.get("stage")) for item in matrix}
    for stage in REQUIRED_STAGES:
        if stage not in stages_present:
            errors.append(f"Missing stage: {stage}")

    for item in matrix:
        stage = str(item.get("stage"))
        unit_tests = item.get("unit_tests")
        integration_tests = item.get("integration_tests")
        if not unit_tests:
            errors.append(f"Stage {stage} missing unit tests")
        if not integration_tests:
            errors.append(f"Stage {stage} missing integration tests")
    return errors


def run_matrix_gate(matrix_path: Path) -> list[GateResult]:
    matrix = load_test_matrix(matrix_path)
    errors = validate_test_matrix(matrix)
    if not errors:
        return [GateResult("pass", "matrix", None, None, "Test matrix complete")]
    return [GateResult("fail", "matrix", None, None, "; ".join(errors))]


def prepare_determinism_run(config_path: Path, run_dir: Path) -> None:
    config = _load_json_or_yaml(config_path)
    golden_dir = Path(str(config.get("golden_dir", ""))).resolve()
    if not golden_dir.exists():
        raise ValueError("Golden directory does not exist")
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(golden_dir, run_dir)


def _compare_files(golden_dir: Path, run_dir: Path) -> list[str]:
    mismatches: list[str] = []
    for path in golden_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(golden_dir)
        candidate = run_dir / relative
        if not candidate.exists():
            mismatches.append(f"Missing file: {relative}")
            continue
        if path.read_bytes() != candidate.read_bytes():
            mismatches.append(f"Mismatch: {relative}")
    return mismatches


def _check_ordering(ordering_path: Path, ordering_key: str) -> list[str]:
    if not ordering_path.exists():
        return ["Ordering file missing"]
    payload = json.loads(ordering_path.read_text(encoding="utf-8"))
    values = payload.get(ordering_key)
    if not isinstance(values, list):
        return ["Ordering payload missing list"]
    if values != sorted(values):
        return ["Ordering not stable"]
    return []


def run_determinism_gate(config_path: Path, run_dir: Path) -> list[GateResult]:
    config = _load_json_or_yaml(config_path)
    golden_dir = Path(str(config.get("golden_dir", ""))).resolve()
    ordering_file = str(config.get("ordering_file", "ordering.json"))
    ordering_key = str(config.get("ordering_key", "ids"))

    mismatches = _compare_files(golden_dir, run_dir)
    ordering_errors = _check_ordering(run_dir / ordering_file, ordering_key)

    errors = mismatches + ordering_errors
    if not errors:
        return [GateResult("pass", "determinism", None, None, "Determinism checks passed")]
    return [GateResult("fail", "determinism", None, None, "; ".join(errors))]


def evaluate_performance_gates(config_path: Path, metrics: dict[str, float]) -> list[GateResult]:
    config = _load_json_or_yaml(config_path)
    gates = config.get("gates", [])
    results: list[GateResult] = []
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        metric = str(gate.get("metric"))
        target = float(gate.get("target", 0.0))
        allowance = float(gate.get("allowance", 0.0))
        observed = metrics.get(metric)
        if observed is None:
            results.append(GateResult("fail", metric, target, None, "Missing metric"))
            continue
        threshold = target * (1.0 + allowance)
        if observed > threshold:
            results.append(
                GateResult(
                    "fail",
                    metric,
                    threshold,
                    observed,
                    f"Performance regression: {observed} > {threshold}",
                )
            )
        else:
            results.append(
                GateResult(
                    "pass",
                    metric,
                    threshold,
                    observed,
                    "Performance within threshold",
                )
            )
    return results
