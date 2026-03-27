from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from auditgraph.storage.safe_artifacts import write_text_redacted
from auditgraph.utils.paths import ensure_within_base
from auditgraph.utils.redaction import Redactor


def resolve_output_path(root: Path, job_name: str, output_path: str | None) -> Path:
    base = (root / "exports").resolve()
    if output_path:
        target = Path(output_path)
        resolved = target.resolve() if target.is_absolute() else (root / target).resolve()
        ensure_within_base(resolved, base, label="job output path")
        return resolved
    return (root / "exports" / "reports" / f"{job_name}.md").resolve()


def report_changed_since(pkg_root: Path, output_path: Path, redactor: Redactor, since_hours: int = 24) -> Path:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    runs_dir = pkg_root / "runs"
    lines = [f"# Changes since {since_hours}h", "", f"Cutoff: {cutoff.isoformat()}"]
    if runs_dir.exists():
        for run in sorted(runs_dir.iterdir()):
            if not run.is_dir():
                continue
            lines.append(f"- {run.name}")
    write_text_redacted(output_path, "\n".join(lines), redactor)
    return output_path
