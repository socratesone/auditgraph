from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import read_json


def diff_runs(pkg_root: Path, run_a: str, run_b: str) -> dict[str, object]:
    path_a = pkg_root / "runs" / run_a / "ingest-manifest.json"
    path_b = pkg_root / "runs" / run_b / "ingest-manifest.json"
    if not path_a.exists() or not path_b.exists():
        return {"status": "missing_manifest", "run_a": run_a, "run_b": run_b}

    manifest_a = read_json(path_a)
    manifest_b = read_json(path_b)
    records_a = {record["path"]: record for record in manifest_a.get("records", [])}
    records_b = {record["path"]: record for record in manifest_b.get("records", [])}

    added = sorted(set(records_b) - set(records_a))
    removed = sorted(set(records_a) - set(records_b))
    changed = sorted(
        key for key in records_a.keys() & records_b.keys() if records_a[key] != records_b[key]
    )

    return {
        "status": "ok",
        "run_a": run_a,
        "run_b": run_b,
        "added": added,
        "removed": removed,
        "changed": changed,
    }
