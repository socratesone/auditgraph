from __future__ import annotations

from typing import Iterable

from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION
from auditgraph.storage.manifests import IngestManifest, IngestRecord


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
    warnings: list[dict[str, str]] | None = None,
    wall_clock_started_at: str | None = None,
    wall_clock_finished_at: str | None = None,
) -> IngestManifest:
    record_list = list(records)
    failed = sum(1 for record in record_list if record.parse_status == "failed")
    skipped = sum(1 for record in record_list if record.parse_status == "skipped")
    ingested = sum(1 for record in record_list if record.parse_status == "ok")
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
        failed_count=failed,
        warnings=list(warnings) if warnings else [],
        wall_clock_started_at=wall_clock_started_at,
        wall_clock_finished_at=wall_clock_finished_at,
    )
