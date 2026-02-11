from __future__ import annotations

from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.errors import JobConfigError, JobNotFoundError
from auditgraph.jobs.config import load_jobs_config, resolve_jobs_path
from auditgraph.jobs.reports import record_job_run, report_changed_since, resolve_output_path
from auditgraph.storage.artifacts import profile_pkg_root
from auditgraph.utils.redaction import build_redactor


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
        raise JobNotFoundError(f"Job not found: {name}")

    action = job.get("action", {})
    action_type = action.get("type")
    args = action.get("args", {})
    output = job.get("output", {})
    output_path = resolve_output_path(root, name, output.get("path"))

    redactor = build_redactor(root, config)

    pkg_root = profile_pkg_root(root, config)
    if action_type == "report.changed_since":
        since = int(args.get("since", "24h").replace("h", "") or 24)
        report_changed_since(pkg_root, output_path, redactor, since_hours=since)
        record_job_run(name, "ok", output_path, None, None)
        return {"status": "ok", "job": name, "output": str(output_path)}

    record_job_run(name, "failed", output_path, None, None)
    raise JobConfigError(f"Unsupported job action: {action_type}")
