from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json
from auditgraph.storage.manifests import IngestManifest, IngestRecord


def write_ingest_manifest(root: Path, manifest: IngestManifest) -> Path:
    manifest_path = root / ".pkg" / "runs" / manifest.run_id / "ingest-manifest.json"
    write_json(manifest_path, manifest.to_dict())
    return manifest_path


def build_manifest(run_id: str, started_at: str, records: Iterable[IngestRecord]) -> IngestManifest:
    return IngestManifest(run_id=run_id, started_at=started_at, records=list(records))
