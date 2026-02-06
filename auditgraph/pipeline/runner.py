from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.ingest import (
    build_manifest,
    build_source_record,
    discover_files,
    load_policy,
    parse_file,
)
from auditgraph.ingest.policy import SKIP_REASON_UNSUPPORTED
from auditgraph.ingest.scanner import split_allowed
from auditgraph.ingest.importer import split_imported
import json

from auditgraph.storage.artifacts import profile_pkg_root, write_json, write_text
from auditgraph.storage.config_snapshot import write_config_snapshot
from auditgraph.storage.hashing import deterministic_run_id, inputs_hash, outputs_hash, sha256_text
from auditgraph.storage.provenance import ProvenanceRecord, write_provenance_index
from auditgraph.storage.audit import DEFAULT_PIPELINE_VERSION


@dataclass
class StageResult:
    stage: str
    status: str
    detail: dict[str, Any]


class PipelineRunner:
    def run_stage(self, stage: str, **kwargs: Any) -> StageResult:
        if stage == "ingest":
            return self.run_ingest(**kwargs)
        if stage == "rebuild":
            return self.run_rebuild(**kwargs)
        return StageResult(stage=stage, status="not_implemented", detail=kwargs)

    def run_ingest(self, root: Path, config: Config) -> StageResult:
        profile = config.profile()
        policy = load_policy(profile)
        include_paths = profile.get("include_paths", [])
        exclude_globs = profile.get("exclude_globs", [])

        files = discover_files(root, include_paths, exclude_globs)
        allowed, skipped = split_allowed(files, policy)
        pkg_root = profile_pkg_root(root, config)
        records = []
        for path in allowed:
            result = parse_file(path, policy)
            record, metadata = build_source_record(
                path,
                root,
                result.parser_id,
                result.status,
                skip_reason=result.skip_reason,
                extra_metadata=result.metadata,
            )
            records.append(record)

            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json(source_path, metadata)

        for path in skipped:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                skip_reason=SKIP_REASON_UNSUPPORTED,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json(source_path, metadata)

        pipeline_version = str(config.raw.get("run_metadata", {}).get("pipeline_version", DEFAULT_PIPELINE_VERSION))
        input_hash = inputs_hash(records)
        config_hash = sha256_text(json.dumps(config.raw, sort_keys=True))
        run_id = deterministic_run_id(input_hash, config_hash)
        _, config_hash = write_config_snapshot(pkg_root, run_id, config)
        output_hash = outputs_hash(records)

        started_at = "1970-01-01T00:00:00Z"
        manifest = build_manifest(
            run_id=run_id,
            started_at=started_at,
            records=records,
            pipeline_version=pipeline_version,
            config_hash=config_hash,
            inputs_hash=input_hash,
            outputs_hash=output_hash,
        )
        manifest_path = pkg_root / "runs" / run_id / "ingest-manifest.json"
        write_json(manifest_path, manifest.to_dict())
        replay_path = pkg_root / "runs" / run_id / "replay-log.jsonl"
        replay_line = {
            "stage": "ingest",
            "run_id": run_id,
            "inputs": len(records),
            "inputs_hash": input_hash,
            "outputs_hash": output_hash,
            "config_hash": config_hash,
            "pipeline_version": pipeline_version,
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        provenance_records = [
            ProvenanceRecord(
                artifact_id=record.source_hash,
                source_path=record.path,
                source_hash=record.source_hash,
                rule_id="ingest.source.v1",
                input_hash=record.source_hash,
                run_id=run_id,
            )
            for record in records
        ]
        write_provenance_index(pkg_root, run_id, provenance_records)

        return StageResult(
            stage="ingest",
            status="ok",
            detail={
                "files": len(files),
                "manifest": str(manifest_path),
                "profile": config.active_profile(),
            },
        )

    def run_rebuild(self, root: Path, config: Config) -> StageResult:
        return self.run_ingest(root=root, config=config)

    def run_import(self, root: Path, config: Config, targets: list[str]) -> StageResult:
        profile = config.profile()
        policy = load_policy(profile)
        exclude_globs = profile.get("exclude_globs", [])
        allowed, skipped = split_imported(root, targets, exclude_globs, policy)
        pkg_root = profile_pkg_root(root, config)
        records = []
        for path in allowed:
            result = parse_file(path, policy)
            record, metadata = build_source_record(
                path,
                root,
                result.parser_id,
                result.status,
                skip_reason=result.skip_reason,
                extra_metadata=result.metadata,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json(source_path, metadata)

        for path in skipped:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                skip_reason=SKIP_REASON_UNSUPPORTED,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json(source_path, metadata)

        pipeline_version = str(config.raw.get("run_metadata", {}).get("pipeline_version", DEFAULT_PIPELINE_VERSION))
        input_hash = inputs_hash(records)
        config_hash = sha256_text(json.dumps(config.raw, sort_keys=True))
        run_id = deterministic_run_id(input_hash, config_hash)
        _, config_hash = write_config_snapshot(pkg_root, run_id, config)
        output_hash = outputs_hash(records)

        started_at = "1970-01-01T00:00:00Z"
        manifest = build_manifest(
            run_id=run_id,
            started_at=started_at,
            records=records,
            pipeline_version=pipeline_version,
            config_hash=config_hash,
            inputs_hash=input_hash,
            outputs_hash=output_hash,
        )
        manifest_path = pkg_root / "runs" / run_id / "ingest-manifest.json"
        write_json(manifest_path, manifest.to_dict())

        provenance_records = [
            ProvenanceRecord(
                artifact_id=record.source_hash,
                source_path=record.path,
                source_hash=record.source_hash,
                rule_id="ingest.source.v1",
                input_hash=record.source_hash,
                run_id=run_id,
            )
            for record in records
        ]
        write_provenance_index(pkg_root, run_id, provenance_records)

        return StageResult(
            stage="import",
            status="ok",
            detail={
                "files": len(records),
                "manifest": str(manifest_path),
                "profile": config.active_profile(),
            },
        )

