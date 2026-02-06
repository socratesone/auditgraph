from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditgraph.config import Config
from auditgraph.ingest import build_manifest, build_source_record, discover_files, parse_file
import json

from auditgraph.storage.artifacts import profile_pkg_root, write_json, write_text
from auditgraph.storage.hashing import sha256_text


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
        include_paths = profile.get("include_paths", [])
        exclude_globs = profile.get("exclude_globs", [])

        files = discover_files(root, include_paths, exclude_globs)
        pkg_root = profile_pkg_root(root, config)
        records = []
        for path in files:
            parser_id, parse_status, _ = parse_file(path)
            record, metadata = build_source_record(path, root, parser_id, parse_status)
            records.append(record)

            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json(source_path, metadata)

        run_id = self._compute_run_id(records, config)
        started_at = "1970-01-01T00:00:00Z"
        manifest = build_manifest(run_id=run_id, started_at=started_at, records=records)
        manifest_path = pkg_root / "runs" / run_id / "ingest-manifest.json"
        write_json(manifest_path, manifest.to_dict())
        replay_path = pkg_root / "runs" / run_id / "replay-log.jsonl"
        replay_line = {
            "stage": "ingest",
            "run_id": run_id,
            "inputs": len(records),
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

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

    def _compute_run_id(self, records: list[Any], config: Config) -> str:
        record_hashes = ":".join(sorted(record.source_hash for record in records))
        config_hash = sha256_text(str(config.raw))
        return f"run_{sha256_text(record_hashes + config_hash)}"
