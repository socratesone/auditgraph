from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from auditgraph.errors import BudgetError

MIN_SOURCE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class BudgetStatus:
    status: str
    usage_ratio: float
    limit_bytes: int
    projected_bytes: int
    message: str


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def _latest_manifest_path(pkg_root: Path) -> Path | None:
    runs_dir = pkg_root / "runs"
    if not runs_dir.exists():
        return None
    candidates: list[Path] = []
    for entry in runs_dir.iterdir():
        if not entry.is_dir():
            continue
        manifest = entry / "ingest-manifest.json"
        if manifest.exists():
            candidates.append(manifest)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.as_posix())[-1]


def latest_source_bytes(pkg_root: Path) -> int:
    manifest_path = _latest_manifest_path(pkg_root)
    if not manifest_path:
        return 0
    payload = manifest_path.read_text(encoding="utf-8")
    try:
        import json

        manifest = json.loads(payload)
    except Exception as exc:
        raise BudgetError("Failed to parse ingest manifest for budget check") from exc

    records = manifest.get("records", [])
    if not isinstance(records, list):
        return 0
    total = 0
    for record in records:
        try:
            total += int(record.get("size", 0))
        except Exception:
            continue
    return total


def evaluate_budget(
    source_bytes: int,
    artifact_bytes: int,
    settings: dict[str, object],
    *,
    additional_bytes: int = 0,
) -> BudgetStatus:
    multiplier = float(settings.get("multiplier", 3.0))
    warn_threshold = float(settings.get("warn_threshold", 0.8))
    block_threshold = float(settings.get("block_threshold", 1.0))

    base_source = max(int(source_bytes), MIN_SOURCE_BYTES)
    limit_bytes = int(base_source * multiplier)
    projected_bytes = int(artifact_bytes + additional_bytes)
    usage_ratio = projected_bytes / limit_bytes if limit_bytes else 0.0

    if usage_ratio >= block_threshold:
        status = "block"
    elif usage_ratio >= warn_threshold:
        status = "warn"
    else:
        status = "ok"

    message = (
        f"Budget {status}: projected={projected_bytes}B limit={limit_bytes}B "
        f"ratio={usage_ratio:.2f}"
    )
    return BudgetStatus(status, usage_ratio, limit_bytes, projected_bytes, message)


def evaluate_pkg_budget(
    pkg_root: Path,
    source_bytes: int,
    settings: dict[str, object],
    *,
    additional_bytes: int = 0,
) -> BudgetStatus:
    artifact_bytes = _dir_size(pkg_root)
    return evaluate_budget(source_bytes, artifact_bytes, settings, additional_bytes=additional_bytes)


def enforce_budget(status: BudgetStatus) -> None:
    if status.status == "block":
        raise BudgetError(status.message)
