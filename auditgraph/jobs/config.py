from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.errors import ConfigError, JobConfigError


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ConfigError("YAML configuration requires PyYAML.") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _validate_job_entry(name: str, job: Any) -> None:
    if not isinstance(job, dict):
        raise JobConfigError(f"Job '{name}' must be a mapping.")
    action = job.get("action")
    if not isinstance(action, dict) or not action.get("type"):
        raise JobConfigError(f"Job '{name}' must define action.type.")
    output = job.get("output")
    if output is not None and not isinstance(output, dict):
        raise JobConfigError(f"Job '{name}' output must be a mapping when provided.")


def _apply_output_defaults(name: str, job: dict[str, Any]) -> None:
    output = job.get("output")
    if output is None:
        job["output"] = {"path": f"exports/reports/{name}.md"}
        return
    if isinstance(output, dict):
        output.setdefault("path", f"exports/reports/{name}.md")


def _normalize_jobs(jobs_raw: Any) -> dict[str, Any]:
    if isinstance(jobs_raw, dict):
        for name, job in jobs_raw.items():
            _validate_job_entry(str(name), job)
            _apply_output_defaults(str(name), job)
        return jobs_raw
    if isinstance(jobs_raw, list):
        jobs: dict[str, Any] = {}
        for entry in jobs_raw:
            if not isinstance(entry, dict) or not entry.get("name"):
                raise JobConfigError("Job list entries must include a name.")
            name = str(entry["name"])
            if name in jobs:
                raise JobConfigError(f"Duplicate job name: {name}")
            job = {k: v for k, v in entry.items() if k != "name"}
            _validate_job_entry(name, job)
            _apply_output_defaults(name, job)
            jobs[name] = job
        return jobs
    raise JobConfigError("Jobs configuration must define jobs as a mapping or list.")


def load_jobs_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        raise JobConfigError("Jobs configuration not found.")
    if path.suffix.lower() in {".json"}:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = _load_yaml(path)
    if not isinstance(payload, dict):
        raise JobConfigError("Jobs configuration must be a mapping.")
    if "jobs" not in payload:
        raise JobConfigError("Jobs configuration must include a jobs section.")
    payload["jobs"] = _normalize_jobs(payload.get("jobs"))
    return payload


def resolve_jobs_path(root: Path, config: Config) -> Path:
    return root / "config" / "jobs.yaml"


def discover_jobs_path(root: Path, config: Config) -> Path | None:
    path = resolve_jobs_path(root, config)
    return path if path.exists() else None
