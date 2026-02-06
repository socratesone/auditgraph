from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from auditgraph.storage.artifacts import write_text


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
