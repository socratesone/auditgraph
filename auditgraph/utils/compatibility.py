from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auditgraph.errors import CompatibilityError


@dataclass(frozen=True)
class CompatibilityReport:
    compatible: bool
    current_version: str
    artifact_version: str | None
    message: str


def check_latest_manifest_compatibility(pkg_root: Path, current_version: str) -> CompatibilityReport:
    runs_dir = pkg_root / "runs"
    if not runs_dir.exists():
        return CompatibilityReport(True, current_version, None, "No prior manifests found")

    candidates: list[Path] = []
    for entry in runs_dir.iterdir():
        if not entry.is_dir():
            continue
        manifest = entry / "ingest-manifest.json"
        if manifest.exists():
            candidates.append(manifest)

    if not candidates:
        return CompatibilityReport(True, current_version, None, "No prior manifests found")

    manifest_path = sorted(candidates, key=lambda item: item.as_posix())[-1]
    payload = manifest_path.read_text(encoding="utf-8")
    try:
        import json

        manifest = json.loads(payload)
    except Exception as exc:
        raise CompatibilityError("Failed to parse ingest manifest for compatibility check") from exc

    artifact_version = manifest.get("schema_version")
    if not artifact_version:
        return CompatibilityReport(
            False,
            current_version,
            None,
            "Missing schema_version in manifest; rebuild required",
        )

    if str(artifact_version) != current_version:
        return CompatibilityReport(
            False,
            current_version,
            str(artifact_version),
            "Incompatible schema_version detected; rebuild required",
        )

    return CompatibilityReport(True, current_version, str(artifact_version), "Compatible schema_version")


def ensure_latest_manifest_compatibility(pkg_root: Path, current_version: str) -> None:
    report = check_latest_manifest_compatibility(pkg_root, current_version)
    if report.compatible:
        return
    raise CompatibilityError(
        f"{report.message}. Current={report.current_version}, Existing={report.artifact_version or 'unknown'}. "
        "Run 'auditgraph rebuild' to regenerate artifacts."
    )
