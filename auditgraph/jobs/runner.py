from __future__ import annotations

from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.jobs.config import load_jobs_config, resolve_jobs_path
from auditgraph.jobs.reports import report_changed_since
from auditgraph.storage.artifacts import profile_pkg_root


def list_jobs(root: Path, config: Config) -> list[str]:
    jobs_path = resolve_jobs_path(root, config)
    payload = load_jobs_config(jobs_path)
    return sorted(payload.get("jobs", {}).keys())


def run_job(root: Path, config: Config, name: str) -> dict[str, Any]:
    jobs_path = resolve_jobs_path(root, config)
    payload = load_jobs_config(jobs_path)
    jobs = payload.get("jobs", {})
    job = jobs.get(name)
    if not job:
        return {"status": "missing_job", "job": name}

    action = job.get("action", {})
    action_type = action.get("type")
    args = action.get("args", {})
    output = job.get("output", {})
    output_path = Path(output.get("path", "exports/reports/job.md"))
    output_path = (root / output_path).resolve()

    pkg_root = profile_pkg_root(root, config)
    if action_type == "report.changed_since":
        since = int(args.get("since", "24h").replace("h", "") or 24)
        report_changed_since(pkg_root, output_path, since_hours=since)
        return {"status": "ok", "job": name, "output": str(output_path)}

    return {"status": "unsupported_action", "job": name, "type": action_type}
