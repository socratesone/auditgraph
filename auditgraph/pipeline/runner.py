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

from auditgraph.extract.code_symbols import extract_code_symbols
from auditgraph.extract.entities import build_entity, build_note_entity
from auditgraph.extract.manifest import extract_adr_claims, extract_log_claims, write_claims, write_entities
from auditgraph.link import build_source_cooccurrence_links, write_links
from auditgraph.link.adjacency import write_adjacency
from auditgraph.index.bm25 import build_bm25_index
from auditgraph.index.semantic import build_semantic_index
from auditgraph.storage.artifacts import profile_pkg_root, read_json, write_json, write_text
from auditgraph.storage.config_snapshot import write_config_snapshot
from auditgraph.storage.hashing import deterministic_run_id, inputs_hash, outputs_hash, sha256_json, sha256_text
from auditgraph.storage.loaders import load_entities
from auditgraph.storage.provenance import ProvenanceRecord, write_provenance_index
from auditgraph.storage.audit import DEFAULT_PIPELINE_VERSION
from auditgraph.storage.manifests import StageManifest


@dataclass
class StageResult:
    stage: str
    status: str
    detail: dict[str, Any]


class PipelineRunner:
    _deterministic_time = "1970-01-01T00:00:00Z"

    def run_stage(self, stage: str, **kwargs: Any) -> StageResult:
        if stage == "ingest":
            return self.run_ingest(**kwargs)
        if stage == "normalize":
            return self.run_normalize(**kwargs)
        if stage == "extract":
            return self.run_extract(**kwargs)
        if stage == "link":
            return self.run_link(**kwargs)
        if stage == "index":
            return self.run_index(**kwargs)
        if stage == "rebuild":
            return self.run_rebuild(**kwargs)
        return StageResult(stage=stage, status="not_implemented", detail=kwargs)

    def _resolve_run_id(self, pkg_root: Path, run_id: str | None) -> str | None:
        if run_id:
            return run_id
        runs_dir = pkg_root / "runs"
        if not runs_dir.exists():
            return None
        candidates = []
        for entry in runs_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest = entry / "ingest-manifest.json"
            if manifest.exists():
                candidates.append(entry.name)
        return sorted(candidates)[-1] if candidates else None

    def _load_ingest_manifest(self, pkg_root: Path, run_id: str) -> dict[str, Any] | None:
        manifest_path = pkg_root / "runs" / run_id / "ingest-manifest.json"
        if not manifest_path.exists():
            return None
        return read_json(manifest_path)

    def _load_stage_manifest(self, pkg_root: Path, run_id: str, stage: str) -> dict[str, Any] | None:
        manifest_path = pkg_root / "runs" / run_id / f"{stage}-manifest.json"
        if not manifest_path.exists():
            return None
        return read_json(manifest_path)

    def _write_stage_manifest(
        self,
        pkg_root: Path,
        stage: str,
        run_id: str,
        inputs_hash: str,
        outputs_hash: str,
        config_hash: str,
        artifacts: list[str],
        status: str = "ok",
    ) -> Path:
        manifest = StageManifest(
            version="v1",
            stage=stage,
            run_id=run_id,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            status=status,
            started_at=self._deterministic_time,
            finished_at=self._deterministic_time,
            artifacts=artifacts,
        )
        manifest_path = pkg_root / "runs" / run_id / f"{stage}-manifest.json"
        write_json(manifest_path, manifest.to_dict())
        return manifest_path

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

        artifacts = [
            str(pkg_root / "sources" / f"{record.source_hash}.json")
            for record in records
        ]
        manifest = build_manifest(
            run_id=run_id,
            started_at=self._deterministic_time,
            finished_at=self._deterministic_time,
            records=records,
            pipeline_version=pipeline_version,
            config_hash=config_hash,
            inputs_hash=input_hash,
            outputs_hash=output_hash,
            artifacts=artifacts,
            status="ok",
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

    def run_normalize(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="normalize", status="missing_manifest", detail={"run_id": run_id})
        manifest = self._load_ingest_manifest(pkg_root, resolved)
        if not manifest:
            return StageResult(stage="normalize", status="missing_manifest", detail={"run_id": resolved})

        inputs_hash = str(manifest.get("outputs_hash", ""))
        outputs_hash = inputs_hash
        config_hash = str(manifest.get("config_hash", ""))
        artifacts = [str(path) for path in manifest.get("artifacts", [])]
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="normalize",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
        )
        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "normalize",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")
        return StageResult(
            stage="normalize",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_extract(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="extract", status="missing_manifest", detail={"run_id": run_id})
        ingest_manifest = self._load_ingest_manifest(pkg_root, resolved)
        if not ingest_manifest:
            return StageResult(stage="extract", status="missing_manifest", detail={"run_id": resolved})

        records = ingest_manifest.get("records", [])
        source_map = {record["path"]: record["source_hash"] for record in records}
        ok_paths = [
            root / record["path"]
            for record in records
            if record.get("parse_status") == "ok"
        ]

        entities: dict[str, dict[str, object]] = {}
        claims: list[dict[str, object]] = []

        for record in records:
            if record.get("parse_status") != "ok":
                continue
            source_path = str(record["path"])
            source_hash = str(record["source_hash"])
            source_meta_path = pkg_root / "sources" / f"{source_hash}.json"
            meta = read_json(source_meta_path) if source_meta_path.exists() else {}
            parser_id = str(record.get("parser_id", ""))
            if parser_id == "text/markdown":
                frontmatter = meta.get("frontmatter") if isinstance(meta, dict) else None
                title = None
                if isinstance(frontmatter, dict):
                    title = frontmatter.get("title")
                if not title:
                    title = Path(source_path).stem
                note_entity = build_note_entity(str(title), source_path, source_hash)
                entities[note_entity["id"]] = note_entity

        code_symbols = extract_code_symbols(root, ok_paths)
        for symbol in code_symbols:
            source_path = str(symbol.get("source_path", ""))
            source_hash = str(source_map.get(source_path, ""))
            entity = build_entity(symbol, source_hash)
            entities[entity["id"]] = entity

        adr_claims = extract_adr_claims(pkg_root, ok_paths)
        if adr_claims:
            claims.extend(adr_claims)

        log_claims = extract_log_claims(ok_paths)
        if log_claims:
            claims.extend(log_claims)

        entity_list = list(entities.values())
        entity_paths = write_entities(pkg_root, entity_list)
        claim_paths = write_claims(pkg_root, claims)

        outputs_hash = sha256_json(
            {
                "entities": sorted(entity["id"] for entity in entity_list),
                "claims": sorted(claim.get("id") for claim in claims),
            }
        )
        inputs_hash = str(ingest_manifest.get("outputs_hash", ""))
        config_hash = str(ingest_manifest.get("config_hash", ""))
        artifacts = [str(path) for path in entity_paths + claim_paths]
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="extract",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
        )

        provenance_records: list[ProvenanceRecord] = []
        for entity in entity_list:
            refs = entity.get("refs", [])
            ref = refs[0] if isinstance(refs, list) and refs else {}
            provenance_records.append(
                ProvenanceRecord(
                    artifact_id=str(entity.get("id")),
                    source_path=str(ref.get("source_path", "")),
                    source_hash=str(ref.get("source_hash", "")),
                    rule_id=str(entity.get("provenance", {}).get("created_by_rule", "")),
                    input_hash=str(entity.get("provenance", {}).get("input_hash", "")),
                    run_id=resolved,
                )
            )
        for claim in claims:
            provenance = claim.get("provenance", {}) if isinstance(claim, dict) else {}
            provenance_records.append(
                ProvenanceRecord(
                    artifact_id=str(claim.get("id")),
                    source_path=str(provenance.get("source_file", "")),
                    source_hash="",
                    rule_id=str(provenance.get("extractor_rule_id", "")),
                    input_hash=str(claim.get("id")),
                    run_id=resolved,
                )
            )
        write_provenance_index(pkg_root, resolved, provenance_records)

        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "extract",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        return StageResult(
            stage="extract",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_link(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="link", status="missing_manifest", detail={"run_id": run_id})

        extract_manifest = self._load_stage_manifest(pkg_root, resolved, "extract")
        if not extract_manifest:
            return StageResult(stage="link", status="missing_manifest", detail={"run_id": resolved})

        entities = load_entities(pkg_root)
        links = build_source_cooccurrence_links(entities)
        link_paths = write_links(pkg_root, links)

        adjacency: dict[str, list[dict[str, object]]] = {}
        for link in links:
            from_id = str(link.get("from_id", ""))
            if not from_id:
                continue
            adjacency.setdefault(from_id, []).append(
                {
                    "to_id": link.get("to_id"),
                    "type": link.get("type"),
                    "rule_id": link.get("rule_id"),
                    "evidence": link.get("evidence", []),
                    "authority": link.get("authority"),
                }
            )
        for edges in adjacency.values():
            edges.sort(
                key=lambda item: (
                    str(item.get("type", "")),
                    str(item.get("rule_id", "")),
                    str(item.get("to_id", "")),
                )
            )
        adjacency_path = write_adjacency(pkg_root, adjacency)

        outputs_hash = sha256_json(
            {
                "links": sorted(link.get("id") for link in links),
                "adjacency": sorted(adjacency.keys()),
            }
        )
        inputs_hash = str(extract_manifest.get("outputs_hash", ""))
        config_hash = str(extract_manifest.get("config_hash", ""))
        artifacts = [str(path) for path in link_paths] + [str(adjacency_path)]
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="link",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
        )

        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "link",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        return StageResult(
            stage="link",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_index(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="index", status="missing_manifest", detail={"run_id": run_id})

        link_manifest = self._load_stage_manifest(pkg_root, resolved, "link")
        if not link_manifest:
            return StageResult(stage="index", status="missing_manifest", detail={"run_id": resolved})

        entities = load_entities(pkg_root)
        bm25_path = build_bm25_index(pkg_root, entities)

        search_cfg = config.profile().get("search", {})
        semantic_cfg = search_cfg.get("semantic", {}) if isinstance(search_cfg, dict) else {}
        semantic_enabled = bool(semantic_cfg.get("enabled", False))
        semantic_path = None
        if semantic_enabled:
            semantic_path = build_semantic_index(pkg_root, [])

        outputs_hash = sha256_json({"bm25": str(bm25_path), "semantic": str(semantic_path)})
        inputs_hash = str(link_manifest.get("outputs_hash", ""))
        config_hash = str(link_manifest.get("config_hash", ""))
        artifacts = [str(bm25_path)]
        if semantic_path:
            artifacts.append(str(semantic_path))
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="index",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
        )

        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "index",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
        }
        write_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        return StageResult(
            stage="index",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_rebuild(self, root: Path, config: Config) -> StageResult:
        ingest = self.run_ingest(root=root, config=config)
        if ingest.status != "ok":
            return ingest
        manifest_path = Path(str(ingest.detail.get("manifest", "")))
        run_id = manifest_path.parent.name if manifest_path.exists() else None
        normalize = self.run_normalize(root=root, config=config, run_id=run_id)
        if normalize.status != "ok":
            return normalize
        extract = self.run_extract(root=root, config=config, run_id=run_id)
        if extract.status != "ok":
            return extract
        link = self.run_link(root=root, config=config, run_id=run_id)
        if link.status != "ok":
            return link
        index = self.run_index(root=root, config=config, run_id=run_id)
        if index.status != "ok":
            return index
        return StageResult(
            stage="rebuild",
            status="ok",
            detail={"run_id": run_id, "manifest": index.detail.get("manifest")},
        )

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

        artifacts = [
            str(pkg_root / "sources" / f"{record.source_hash}.json")
            for record in records
        ]
        manifest = build_manifest(
            run_id=run_id,
            started_at=self._deterministic_time,
            finished_at=self._deterministic_time,
            records=records,
            pipeline_version=pipeline_version,
            config_hash=config_hash,
            inputs_hash=input_hash,
            outputs_hash=output_hash,
            artifacts=artifacts,
            status="ok",
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

