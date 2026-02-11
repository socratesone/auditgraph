from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import write_json
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION
from auditgraph.storage.manifests import IngestManifest, IngestRecord


def write_ingest_manifest(root: Path, manifest: IngestManifest) -> Path:
    manifest_path = root / ".pkg" / "runs" / manifest.run_id / "ingest-manifest.json"
    write_json(manifest_path, manifest.to_dict())
    return manifest_path


def build_manifest(
    run_id: str,
    started_at: str,
    finished_at: str,
    records: Iterable[IngestRecord],
    pipeline_version: str,
    config_hash: str,
    inputs_hash: str,
    outputs_hash: str,
    artifacts: list[str],
    status: str,
) -> IngestManifest:
    record_list = list(records)
    skipped = sum(1 for record in record_list if record.parse_status == "skipped")
    ingested = len(record_list) - skipped
    return IngestManifest(
        version="v1",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        stage="ingest",
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        pipeline_version=pipeline_version,
        config_hash=config_hash,
        inputs_hash=inputs_hash,
        outputs_hash=outputs_hash,
        status=status,
        artifacts=artifacts,
        records=record_list,
        ingested_count=ingested,
        skipped_count=skipped,
    )
