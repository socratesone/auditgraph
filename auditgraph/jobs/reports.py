from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from auditgraph.storage.artifacts import write_text


@dataclass(frozen=True)
class JobRun:
    job_name: str
    status: str
    output_path: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def resolve_output_path(root: Path, job_name: str, output_path: str | None) -> Path:
    if output_path:
        return (root / output_path).resolve()
    return (root / "exports" / "reports" / f"{job_name}.md").resolve()


def record_job_run(
    job_name: str,
    status: str,
    output_path: Path,
    started_at: Optional[str],
    finished_at: Optional[str],
) -> JobRun:
    return JobRun(
        job_name=job_name,
        status=status,
        output_path=str(output_path),
        started_at=started_at,
        finished_at=finished_at,
    )


def report_changed_since(pkg_root: Path, output_path: Path, since_hours: int = 24) -> Path:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    runs_dir = pkg_root / "runs"
    lines = [f"# Changes since {since_hours}h", "", f"Cutoff: {cutoff.isoformat()}"]
    if runs_dir.exists():
        for run in sorted(runs_dir.iterdir()):
            if not run.is_dir():
                continue
            lines.append(f"- {run.name}")
    write_text(output_path, "\n".join(lines))
    return output_path
