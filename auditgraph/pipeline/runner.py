from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditgraph.config import Config, footprint_budget_settings
from auditgraph.ingest import (
    build_manifest,
    build_source_record,
    discover_files,
    load_policy,
    parse_file,
)
from auditgraph.ingest.policy import SKIP_REASON_UNSUPPORTED, SKIP_REASON_SYMLINK_REFUSED
from auditgraph.ingest.policy import SKIP_REASON_UNCHANGED, parser_id_for
from auditgraph.ingest.scanner import discover_files_with_refusals, split_allowed
from auditgraph.ingest.importer import split_imported, split_imported_with_refusals
import sys
import json

from auditgraph.extract.entities import build_note_entity
from auditgraph.extract.manifest import extract_adr_claims, extract_log_claims, write_claims, write_entities
from auditgraph.link import build_source_cooccurrence_links, write_links
from auditgraph.link.adjacency import write_adjacency
from auditgraph.index.adjacency_builder import build_adjacency_index
from auditgraph.index.bm25 import build_bm25_index
from auditgraph.index.type_index import build_link_type_indexes, build_type_indexes
from auditgraph.storage.artifacts import append_text, profile_pkg_root, read_json, write_json
from auditgraph.storage.artifacts import write_document_artifacts
from auditgraph.storage.safe_artifacts import write_json_redacted
from auditgraph.utils.redaction import build_redactor
from auditgraph.storage.config_snapshot import ingestion_config_hash, write_config_snapshot
from auditgraph.storage.hashing import deterministic_run_id, deterministic_timestamp, inputs_hash, outputs_hash, sha256_json, sha256_text
from auditgraph.storage.hashing import deterministic_document_id, sha256_file
from auditgraph.storage.loaders import load_entities
from auditgraph.storage.provenance import ProvenanceRecord, write_provenance_index
from auditgraph.storage.audit import ARTIFACT_SCHEMA_VERSION, DEFAULT_PIPELINE_VERSION
from auditgraph.storage.manifests import StageManifest
from auditgraph.utils.compatibility import check_latest_manifest_compatibility, ensure_latest_manifest_compatibility
from auditgraph.utils.budget import evaluate_pkg_budget, enforce_budget


@dataclass
class StageResult:
    stage: str
    status: str
    detail: dict[str, Any]


_LEGACY_CACHE_SKIP_REASONS = {"unchanged_source_hash", SKIP_REASON_UNCHANGED}


def _markdown_document_is_complete(document_payload: dict[str, Any]) -> bool:
    """Spec-028 FR-016b1: a cached markdown document payload is considered
    complete for spec-028 extraction iff the ``text`` field is present and
    non-empty. Pre-028 cached records don't have ``text`` and MUST trigger
    a one-time reparse on the next run.
    """
    if document_payload.get("mime_type") != "text/markdown":
        # Non-markdown documents never had a text requirement.
        return True
    text = document_payload.get("text")
    return isinstance(text, str) and len(text) > 0


def _prune_markdown_subentities_for_source(pkg_root: Path, source_path: str) -> None:
    """Spec-028 FR-016c/FR-016d: delete stale markdown sub-entities and
    their markdown-produced links for a given source path, BEFORE writing
    refreshed entities for the same source.

    Algorithm (data-model.md §5):
      1. Enumerate entities with type ∈ MARKDOWN_ENTITY_TYPES AND
         refs[0].source_path == source_path; collect IDs into stale_ids;
         delete those files.
      2. Enumerate link files with rule_id ∈ MARKDOWN_RULE_IDS AND
         (from_id ∈ stale_ids OR to_id ∈ stale_ids); delete them.

    Links do NOT carry source_path; we resolve source ownership via
    entity IDs instead. This also correctly handles `contains_section`
    edges where from-side is the note entity (not in stale_ids) by
    matching the to-side.
    """
    from auditgraph.extract.markdown import MARKDOWN_ENTITY_TYPES, MARKDOWN_RULE_IDS

    entities_dir = pkg_root / "entities"
    links_dir = pkg_root / "links"
    stale_ids: set[str] = set()

    if entities_dir.exists():
        for entity_file in sorted(entities_dir.rglob("*.json")):
            try:
                payload = read_json(entity_file)
            except Exception:
                continue
            if payload.get("type") not in MARKDOWN_ENTITY_TYPES:
                continue
            refs = payload.get("refs") or []
            if not refs or not isinstance(refs[0], dict):
                continue
            if refs[0].get("source_path") != source_path:
                continue
            stale_ids.add(str(payload.get("id", "")))
            try:
                entity_file.unlink()
            except FileNotFoundError:
                pass

    if not stale_ids:
        return

    if links_dir.exists():
        markdown_rule_set = set(MARKDOWN_RULE_IDS)
        for link_file in sorted(links_dir.rglob("*.json")):
            try:
                link = read_json(link_file)
            except Exception:
                continue
            if link.get("rule_id") not in markdown_rule_set:
                continue
            if link.get("from_id") in stale_ids or link.get("to_id") in stale_ids:
                try:
                    link_file.unlink()
                except FileNotFoundError:
                    pass


def _build_documents_index(
    pkg_root: Path,
    root: Path,  # noqa: ARG001 — retained for signature stability / future use
    normalized_records: list[dict[str, Any]],
) -> "Any":
    """Build a DocumentsIndex from CURRENT run's successful ingest records.

    Spec-028 adjustments3.md §4 AND §5: source-of-truth is the ingest
    manifest (``parse_status == "ok"`` records) joined against the on-disk
    ``documents/<doc_id>.json`` payloads. We do NOT recompute ``document_id``
    here — we read it from the persisted payload and join on
    ``source_hash`` (which IS unambiguously identical between the record
    and the document payload, regardless of whether ingest happened to
    hash the absolute or relative path form).

    Filtering rules:
      1. Only records with ``parse_status == "ok"`` and a non-empty
         ``source_hash`` qualify.
      2. Only document files whose ``source_hash`` matches a qualifying
         record are added.
      3. Stale document artifacts from prior runs (their sources absent
         from the current manifest) are silently excluded — this is the
         scan-filter behavior adjustments3 §4 mandates.
    """
    from auditgraph.extract.markdown import DocumentsIndex

    # Build: source_hash → (source_path, record_index)
    hash_to_relpath: dict[str, str] = {}
    for record in normalized_records:
        if record.get("parse_status") != "ok":
            continue
        relative_source_path = str(record.get("path", ""))
        source_hash = str(record.get("source_hash", ""))
        if not relative_source_path or not source_hash:
            continue
        hash_to_relpath[source_hash] = relative_source_path

    by_doc_id: dict[str, Path] = {}
    by_source_path: dict[str, str] = {}
    docs_dir = pkg_root / "documents"
    if docs_dir.exists():
        for doc_file in docs_dir.glob("doc_*.json"):
            try:
                payload = read_json(doc_file)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            doc_source_hash = str(payload.get("source_hash", ""))
            doc_id = str(payload.get("document_id", ""))
            if not doc_source_hash or not doc_id:
                continue
            relpath = hash_to_relpath.get(doc_source_hash)
            if relpath is None:
                # Stale document artifact — its source is not in the current
                # ingest manifest. Skip it per adjustments3 §4.
                continue
            by_doc_id[doc_id] = doc_file
            by_source_path[relpath] = doc_id
    return DocumentsIndex(by_doc_id=by_doc_id, by_source_path=by_source_path)


def _normalize_ingest_records(records: Any) -> list[dict[str, Any]]:
    """Translate pre-028 cache-hit records to the canonical shape.

    Spec-028 separates parse outcome (`parse_status`) from execution origin
    (`source_origin`). Pre-028 workspaces wrote cache hits as
    ``parse_status="skipped" + skip_reason="unchanged_source_hash"`` which
    would cause the post-028 extract filter (``parse_status != "ok"``) to
    silently drop them — re-introducing BUG-1 from Orpheus.md.

    This helper returns a shallow copy of ``records`` with the legacy shape
    rewritten to ``parse_status="ok", source_origin="cached"`` in memory.
    The on-disk manifest is NOT mutated (FR-001/FR-002).
    """
    normalized: list[dict[str, Any]] = []
    for record in records or []:
        record_copy = dict(record)
        if (
            record_copy.get("parse_status") == "skipped"
            and record_copy.get("skip_reason") in _LEGACY_CACHE_SKIP_REASONS
        ):
            record_copy["parse_status"] = "ok"
            record_copy["source_origin"] = "cached"
        normalized.append(record_copy)
    return normalized


class PipelineRunner:
    @staticmethod
    def _deterministic_time_for(seed: str) -> str:
        return deterministic_timestamp(seed)

    def run_stage(self, stage: str, **kwargs: Any) -> StageResult:
        if stage == "ingest":
            return self.run_ingest(**kwargs)
        if stage == "git-provenance":
            return self.run_git_provenance(**kwargs)
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
        warnings: list[dict[str, str]] | None = None,
        wall_clock_started_at: str | None = None,
    ) -> Path:
        # Spec-028 US6 (BUG-3 fix): `wall_clock_started_at` is captured by
        # each `run_*` method at stage entry and passed in here.
        # `wall_clock_finished_at` is captured at manifest-construction time
        # so the pair reflects actual stage wall-clock duration. If the
        # caller did not supply a start timestamp (legacy callers), fall
        # back to a single helper call so both fields at least carry a
        # valid ISO string. `started_at`/`finished_at` stay deterministic
        # (hashed from run_id) to preserve byte-identity of non-wall-clock
        # manifest fields across runs.
        from auditgraph.storage.hashing import wall_clock_now

        finished = wall_clock_now()
        started = wall_clock_started_at if wall_clock_started_at is not None else finished
        manifest = StageManifest(
            version="v1",
            schema_version=ARTIFACT_SCHEMA_VERSION,
            stage=stage,
            run_id=run_id,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            status=status,
            started_at=self._deterministic_time_for(run_id),
            finished_at=self._deterministic_time_for(run_id),
            artifacts=artifacts,
            # Spec-028 FR-018: always serialize (even as []).
            warnings=list(warnings) if warnings else [],
            wall_clock_started_at=started,
            wall_clock_finished_at=finished,
        )
        manifest_path = pkg_root / "runs" / run_id / f"{stage}-manifest.json"
        write_json(manifest_path, manifest.to_dict())
        return manifest_path

    def run_ingest(self, root: Path, config: Config, *, enforce_compatibility: bool = True) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
        profile = config.profile()
        policy = load_policy(profile)
        include_paths = profile.get("include_paths", [])
        exclude_globs = profile.get("exclude_globs", [])

        redactor = build_redactor(root, config)

        pkg_root = profile_pkg_root(root, config)
        if enforce_compatibility:
            ensure_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)

        discover_result = discover_files_with_refusals(root, include_paths, exclude_globs)
        allowed, skipped = split_allowed(discover_result.files, policy)
        refused_symlinks = discover_result.refused_symlinks
        records = []
        source_payloads: list[tuple[Any, dict[str, object]]] = []
        ingest_cfg = profile.get("ingestion", {}) if isinstance(profile, dict) else {}
        parse_options = {
            "ocr_mode": ingest_cfg.get("ocr_mode", "off"),
            "chunk_tokens": int(ingest_cfg.get("chunk_tokens", 200)),
            "chunk_overlap_tokens": int(ingest_cfg.get("chunk_overlap_tokens", 40)),
            "max_file_size_bytes": int(ingest_cfg.get("max_file_size_bytes", 209715200)),
            "ingest_config_hash": ingestion_config_hash(config),
            # Spec 027 FR-016: parser-entry redaction is the canonical site.
            # See auditgraph/ingest/parsers.py:_build_document_metadata.
            "redactor": redactor,
        }
        for path in allowed:
            source_hash = sha256_file(path)
            document_id = deterministic_document_id(path.as_posix(), source_hash)
            existing_document_path = pkg_root / "documents" / f"{document_id}.json"
            if existing_document_path.exists():
                existing_document = read_json(existing_document_path)
                if str(existing_document.get("source_hash", "")) == source_hash:
                    # Spec-028 FR-016b1 cache-completeness check: pre-028
                    # cached markdown records lack the `text` field added by
                    # FR-015a. Fall through to the fresh-parse branch once
                    # to populate it; record the result as source_origin="fresh"
                    # (NOT cached). No warning — silent one-time migration.
                    if _markdown_document_is_complete(existing_document):
                        # Spec-028 FR-001/FR-002 (BUG-1 fix): cache hit is
                        # parse_status="ok", source_origin="cached".
                        # Downstream stages admit this record (extract filters
                        # on parse_status=="ok", regardless of origin).
                        record, metadata = build_source_record(
                            path,
                            root,
                            parser_id_for(path),
                            "ok",
                            status_reason=SKIP_REASON_UNCHANGED,
                            skip_reason=SKIP_REASON_UNCHANGED,
                            source_origin="cached",
                        )
                        records.append(record)
                        source_payloads.append((record, metadata))
                        continue
                    # else: fall through to fresh-parse branch below.

            parse_options["source_hash"] = source_hash
            result = parse_file(path, policy, parse_options)
            record, metadata = build_source_record(
                path,
                root,
                result.parser_id,
                result.status,
                status_reason=result.status_reason,
                skip_reason=result.skip_reason,
                extra_metadata=result.metadata,
            )
            records.append(record)
            source_payloads.append((record, metadata))

            document_payload = metadata.get("document") if isinstance(metadata, dict) else None
            segments_payload = metadata.get("segments") if isinstance(metadata, dict) else None
            chunks_payload = metadata.get("chunks") if isinstance(metadata, dict) else None
            if isinstance(document_payload, dict) and isinstance(segments_payload, list) and isinstance(chunks_payload, list):
                # SECURITY (Spec 027 FR-016): payloads are already redacted by
                # the parser entry point (see auditgraph/ingest/parsers.py). The
                # hotfix's post-chunking pass has been retired because it was
                # too late for multi-line secrets (PEM keys straddling a chunk
                # boundary would survive). Parser-entry is the single source of
                # truth — adding a second pass here would mask bugs in the
                # canonical site.
                write_document_artifacts(
                    pkg_root,
                    document_payload,
                    segments_payload,
                    chunks_payload,
                )

        for path in skipped:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                status_reason=SKIP_REASON_UNSUPPORTED,
                skip_reason=SKIP_REASON_UNSUPPORTED,
            )
            records.append(record)
            source_payloads.append((record, metadata))

        # Spec 027 FR-001..FR-004: refused symlinks surface as skipped sources
        # with `skip_reason: symlink_refused`. The file contents are never read.
        for path in refused_symlinks:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                status_reason=SKIP_REASON_SYMLINK_REFUSED,
                skip_reason=SKIP_REASON_SYMLINK_REFUSED,
            )
            records.append(record)
            source_payloads.append((record, metadata))

        # Spec 027 FR-002: single-line stderr warning when ≥ 1 symlink refused.
        if refused_symlinks:
            sys.stderr.write(
                f"WARN: refused {len(refused_symlinks)} symlinks pointing outside "
                f"{root.resolve()} (see manifest for details)\n"
            )

        source_bytes = sum(int(record.size) for record in records)
        budget_settings = footprint_budget_settings(config)
        budget_status = evaluate_pkg_budget(
            pkg_root,
            source_bytes,
            budget_settings,
            additional_bytes=source_bytes,
        )
        enforce_budget(budget_status)

        for record, metadata in source_payloads:
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            # Spec-028 regression fix: on a cache hit the minimal record-only
            # metadata returned by build_source_record lacks `frontmatter`,
            # `document`, `segments`, and `chunks` — the rich fields produced
            # by the fresh parse. If we blindly overwrite, the next extract
            # loses access to the frontmatter title and falls back to the
            # filename stem, duplicating the note entity. Preserve those
            # fields from the existing on-disk metadata when the current
            # write came from a cache hit (source_origin == "cached").
            if record.source_origin == "cached" and source_path.exists():
                try:
                    existing = read_json(source_path)
                except Exception:
                    existing = None
                if isinstance(existing, dict):
                    merged = dict(existing)
                    # Basic fields (parse_status, source_origin, status_reason,
                    # skip_reason, parser_id, size, mtime) come from the fresh
                    # record; everything else stays from the cached payload.
                    merged.update(metadata)
                    metadata = merged
            write_json_redacted(source_path, metadata, redactor)

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
        from auditgraph.storage.hashing import wall_clock_now

        # Spec-028 US6 (BUG-3 fix): wall_clock_started_at was captured at
        # stage entry (near the top of run_ingest / run_import). Capture
        # wall_clock_finished_at now, right before we build the manifest
        # so the pair reflects actual stage duration.
        _wall_clock_finished_at = wall_clock_now()
        manifest = build_manifest(
            run_id=run_id,
            started_at=self._deterministic_time_for(run_id),
            finished_at=self._deterministic_time_for(run_id),
            wall_clock_started_at=_wall_clock_started_at,
            wall_clock_finished_at=_wall_clock_finished_at,
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
            "duration_ms": int((time.monotonic() - _start) * 1000),
        }
        append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

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

        detail = {
            "files": len(discover_result.files),
            "manifest": str(manifest_path),
            "profile": config.active_profile(),
            "ok": sum(1 for record in records if record.parse_status == "ok"),
            "skipped": sum(1 for record in records if record.parse_status == "skipped"),
            "failed": sum(1 for record in records if record.parse_status == "failed"),
            "refused_symlinks": len(refused_symlinks),
        }
        if budget_status.status == "warn":
            detail["budget"] = {
                "status": budget_status.status,
                "usage_ratio": budget_status.usage_ratio,
                "limit_bytes": budget_status.limit_bytes,
                "projected_bytes": budget_status.projected_bytes,
            }
        return StageResult(stage="ingest", status="ok", detail=detail)

    def run_git_provenance(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="git-provenance", status="missing_manifest", detail={"run_id": run_id})

        # Check enabled flag before loading ingest manifest
        profile = config.profile()
        gp_cfg = profile.get("git_provenance", {})
        if not gp_cfg.get("enabled", False):
            return StageResult(stage="git-provenance", status="skipped", detail={"reason": "disabled"})

        ingest_manifest = self._load_ingest_manifest(pkg_root, resolved)
        if not ingest_manifest:
            return StageResult(stage="git-provenance", status="missing_manifest", detail={"run_id": resolved})

        from auditgraph.git.reader import GitReader
        from auditgraph.git.selector import select_commits
        from auditgraph.git.materializer import (
            build_commit_nodes,
            build_author_nodes,
            build_tag_nodes,
            build_repo_node,
            build_ref_nodes,
            build_file_nodes,
            build_links,
            build_reverse_index,
        )
        from auditgraph.git.config import load_git_provenance_config
        from auditgraph.storage.sharding import shard_dir

        # Read git history
        try:
            reader = GitReader(root)
        except (FileNotFoundError, NotADirectoryError, Exception) as exc:
            return StageResult(
                stage="git-provenance",
                status="error",
                detail={"error": str(exc), "root": str(root)},
            )
        try:
            commits = reader.walk_commits()
            tags = reader.list_tags()
            branches = reader.list_branches()

            # Load git provenance config
            git_config = load_git_provenance_config(profile)

            # Build diff_stat and file_paths callables
            diff_stat_cache: dict[str, tuple[int, int]] = {}
            file_paths_cache: dict[str, list[str]] = {}

            def _diff_stats(sha: str) -> tuple[int, int]:
                if sha not in diff_stat_cache:
                    diff_stat_cache[sha] = reader.diff_stat(sha)
                return diff_stat_cache[sha]

            def _file_paths(sha: str) -> list[str]:
                if sha not in file_paths_cache:
                    file_paths_cache[sha] = reader.diff_files(sha)
                return file_paths_cache[sha]

            # Select commits
            selected = select_commits(
                commits=commits,
                tags=tags,
                branches=branches,
                diff_stats=_diff_stats,
                file_paths=_file_paths,
                config=git_config,
            )

            # Materialize nodes
            repo_path = str(root.resolve())
            commit_nodes = build_commit_nodes(selected.commits, repo_path)
            author_nodes = build_author_nodes(selected.commits, repo_path)
            tag_nodes = build_tag_nodes(tags, repo_path)
            repo_node = build_repo_node(repo_path)
            ref_nodes = build_ref_nodes(branches, repo_path)
            file_nodes = build_file_nodes(selected.commits, repo_path)

            # Build links
            links = build_links(
                commit_nodes=commit_nodes,
                author_nodes=author_nodes,
                tag_nodes=tag_nodes,
                repo_node=repo_node,
                selected_commits=selected.commits,
                repo_path=repo_path,
                ref_nodes=ref_nodes,
                branches=branches,
            )

            # Build reverse index from modifies links only
            modifies_links = [lnk for lnk in links if lnk.get("type") == "modifies"]
            reverse_index = build_reverse_index(modifies_links)

            # Write entities to sharded storage. Per Spec 025, file entities
            # are created here (by build_file_nodes), which is the sole
            # creator of file entities in the project. This fixes the
            # pre-existing dangling-reference bug where modifies links pointed
            # at file entities that were never materialized for non-code paths.
            all_entities = commit_nodes + author_nodes + tag_nodes + ref_nodes + [repo_node] + file_nodes
            entity_artifacts: list[str] = []
            for entity in all_entities:
                eid = entity["id"]
                entity_dir = shard_dir(pkg_root / "entities", eid)
                entity_path = entity_dir / f"{eid}.json"
                write_json(entity_path, entity)
                entity_artifacts.append(str(entity_path))

            # Write links to sharded storage
            link_artifacts: list[str] = []
            for link in links:
                lid = link["id"]
                link_dir = shard_dir(pkg_root / "links", lid)
                link_path = link_dir / f"{lid}.json"
                write_json(link_path, link)
                link_artifacts.append(str(link_path))

            # Write reverse index
            idx_dir = pkg_root / "indexes" / "git-provenance"
            idx_path = idx_dir / "file-commits.json"
            write_json(idx_path, reverse_index)

            # Compute hashes
            # inputs_hash: HEAD commit + sorted branch name=head pairs + config_hash
            head_sha = commits[0].sha if commits else ""
            sorted_branch_heads = ":".join(
                sorted(b.name + "=" + b.head_sha for b in branches)
            )
            git_config_hash = sha256_json({
                "enabled": git_config.enabled,
                "max_tier2_commits": git_config.max_tier2_commits,
                "hot_paths": sorted(git_config.hot_paths),
                "cold_paths": sorted(git_config.cold_paths),
            })
            stage_inputs_hash = sha256_text(
                head_sha + ":" + sorted_branch_heads + ":" + git_config_hash
            )

            # outputs_hash: sorted entity IDs + sorted link IDs
            stage_outputs_hash = sha256_json({
                "entities": sorted(e["id"] for e in all_entities),
                "links": sorted(lnk["id"] for lnk in links),
            })

            # Write manifest
            all_artifacts = entity_artifacts + link_artifacts + [str(idx_path)]
            manifest_path = self._write_stage_manifest(
                pkg_root,
                stage="git-provenance",
                run_id=resolved,
                inputs_hash=stage_inputs_hash,
                outputs_hash=stage_outputs_hash,
                config_hash=git_config_hash,
                artifacts=all_artifacts,
                wall_clock_started_at=_wall_clock_started_at,
            )

            # Append replay log
            replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
            replay_line = {
                "stage": "git-provenance",
                "run_id": resolved,
                "inputs_hash": stage_inputs_hash,
                "outputs_hash": stage_outputs_hash,
                "config_hash": git_config_hash,
                "duration_ms": int((time.monotonic() - _start) * 1000),
            }
            append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

            return StageResult(
                stage="git-provenance",
                status="ok",
                detail={
                    "manifest": str(manifest_path),
                    "profile": config.active_profile(),
                    "run_id": resolved,
                    "commit_count": len(commit_nodes),
                    "author_count": len(author_nodes),
                    "tag_count": len(tag_nodes),
                    "ref_count": len(ref_nodes),
                    "repo_count": 1,
                    "link_count": len(links),
                },
            )
        finally:
            reader.close()

    def run_normalize(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
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
            wall_clock_started_at=_wall_clock_started_at,
        )
        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "normalize",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
            "duration_ms": int((time.monotonic() - _start) * 1000),
        }
        append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")
        return StageResult(
            stage="normalize",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_extract(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
        pkg_root = profile_pkg_root(root, config)
        redactor = build_redactor(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="extract", status="missing_manifest", detail={"run_id": run_id})
        ingest_manifest = self._load_ingest_manifest(pkg_root, resolved)
        if not ingest_manifest:
            return StageResult(stage="extract", status="missing_manifest", detail={"run_id": resolved})

        # Spec-028 FR-001/FR-002/FR-003 (BUG-1 fix): normalize legacy cache-hit
        # records (parse_status="skipped" + skip_reason="unchanged_source_hash")
        # to the canonical post-028 shape (parse_status="ok", source_origin="cached")
        # in memory before filtering. This is the backward-compat reader for
        # pre-028 workspaces — it does NOT rewrite the on-disk manifest.
        records = _normalize_ingest_records(ingest_manifest.get("records", []))
        source_map = {record["path"]: record["source_hash"] for record in records}
        ok_paths = [
            root / record["path"]
            for record in records
            if record.get("parse_status") == "ok"
        ]

        entities: dict[str, dict[str, object]] = {}
        claims: list[dict[str, object]] = []
        markdown_links: list[dict[str, object]] = []

        # Spec-028 FR-013/FR-016i: markdown sub-entity extraction is on by
        # default but can be disabled via config. When disabled, BOTH the
        # producer AND the pruning helper stay inert (the flag is a pure
        # activation switch, not a cleanup command).
        extraction_cfg = config.profile().get("extraction", {}) if isinstance(config.profile(), dict) else {}
        markdown_cfg = extraction_cfg.get("markdown", {}) if isinstance(extraction_cfg, dict) else {}
        markdown_enabled = bool(markdown_cfg.get("enabled", True))

        # Spec-028 adjustments3.md §4: build DocumentsIndex from the
        # CURRENT run's successful ingest records only — NOT a disk scan
        # of documents/ — so stale document artifacts from prior runs
        # never falsely classify references as internal.
        documents_index = _build_documents_index(pkg_root, root, records)

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
                note_entity = build_note_entity(str(title), source_path, source_hash, redactor=redactor)
                entities[note_entity["id"]] = note_entity

                # Spec-028 US2: emit ag:section / ag:technology / ag:reference
                # sub-entities from the markdown source. Gated by config flag
                # (FR-013/FR-016i).
                if markdown_enabled:
                    from auditgraph.extract.markdown import extract_markdown_subentities

                    # adjustments3.md §5: use the authoritative document
                    # path from the DocumentsIndex we just built. Do NOT
                    # recompute `deterministic_document_id(source_path, ...)`
                    # with the relative path — ingest computed it with the
                    # absolute path and they won't agree.
                    document_id_value = documents_index.by_source_path.get(source_path)
                    document_payload_path = (
                        documents_index.by_doc_id.get(document_id_value)
                        if document_id_value
                        else None
                    )
                    markdown_text = None
                    if document_payload_path is not None and document_payload_path.exists():
                        document_payload = read_json(document_payload_path)
                        document_id_value = document_payload.get("document_id") or document_id_value
                        markdown_text = document_payload.get("text")

                    # FR-016b2: missing text on a markdown document is an
                    # integration bug — ingest should have caught this via
                    # FR-016b1. Fail loudly rather than silently emit zero.
                    if not isinstance(markdown_text, str) or not markdown_text:
                        raise ValueError(
                            f"Spec-028 FR-016b2: markdown document for {source_path!r} "
                            f"is missing the `text` field. Re-run `auditgraph ingest` to "
                            f"trigger the FR-016b1 cache-migration refresh; the extract "
                            f"stage does not tolerate incomplete document records."
                        )
                    if not document_id_value:
                        document_id_value = deterministic_document_id(
                            (root / source_path).as_posix(), source_hash
                        )

                    # FR-016c pruning: remove stale markdown sub-entities for
                    # this source before writing refreshed ones.
                    _prune_markdown_subentities_for_source(pkg_root, source_path)

                    md_entities, md_links = extract_markdown_subentities(
                        source_path=source_path,
                        source_hash=source_hash,
                        document_id=str(document_id_value),
                        document_anchor_id=str(note_entity["id"]),
                        markdown_text=markdown_text,
                        redactor=redactor,
                        documents_index=documents_index,
                        pipeline_version=str(config.raw.get("run_metadata", {}).get("pipeline_version", DEFAULT_PIPELINE_VERSION)),
                    )
                    for ent in md_entities:
                        entities[ent["id"]] = ent
                    markdown_links.extend(md_links)


        adr_claims = extract_adr_claims(pkg_root, ok_paths)
        if adr_claims:
            claims.extend(adr_claims)

        log_claims = extract_log_claims(ok_paths, redactor=redactor)
        if log_claims:
            claims.extend(log_claims)

        # NER entity extraction from chunks
        ner_config = config.profile().get("extraction", {}).get("ner", {})
        ner_link_paths: list[Path] = []
        if ner_config.get("enabled", False):
            from auditgraph.extract.ner import extract_ner_entities
            ner_entities, ner_links = extract_ner_entities(pkg_root, ner_config)
            for ent in ner_entities:
                entities[ent["id"]] = ent
            # Write NER links directly to the canonical sharded link store so
            # they participate in link/index/adjacency stages and are reachable
            # via `auditgraph neighbors` and the link-type index. Previously
            # NER links were written to pkg_root/ner/links.json as an orphaned
            # intermediate artifact that no other stage consumed (Spec NER bug
            # fix).
            if ner_links:
                ner_link_paths = write_links(pkg_root, ner_links)
            # Clean up any vestigial intermediate artifact from prior runs.
            legacy_ner_links_path = pkg_root / "ner" / "links.json"
            if legacy_ner_links_path.exists():
                legacy_ner_links_path.unlink()
                try:
                    legacy_ner_links_path.parent.rmdir()
                except OSError:
                    pass  # directory not empty; leave it

        entity_list = list(entities.values())
        entity_paths = write_entities(pkg_root, entity_list)
        claim_paths = write_claims(pkg_root, claims)

        # Spec-028 US2: write markdown-generated links (contains_section,
        # mentions_technology, references, resolves_to_document) through the
        # canonical link store so they participate in adjacency / index /
        # query paths.
        markdown_link_paths: list[Path] = []
        if markdown_links:
            markdown_link_paths = write_links(pkg_root, markdown_links)

        # Spec-028 US3 FR-017: binary throughput check. Emit the
        # `no_entities_produced` warning iff ≥1 upstream input from the
        # prior stage AND exactly 0 entities produced here.
        from auditgraph.pipeline.warnings import warning_no_entities

        upstream_ok_inputs = sum(
            1 for record in records if record.get("parse_status") == "ok"
        )
        stage_warnings: list[dict[str, str]] = []
        if upstream_ok_inputs >= 1 and len(entity_list) == 0:
            stage_warnings.append(warning_no_entities(upstream_ok_inputs).to_dict())

        outputs_hash = sha256_json(
            {
                "entities": sorted(entity["id"] for entity in entity_list),
                "claims": sorted(claim.get("id") for claim in claims),
                "ner_links": sorted(str(path) for path in ner_link_paths),
                "markdown_links": sorted(str(path) for path in markdown_link_paths),
            }
        )
        inputs_hash = str(ingest_manifest.get("outputs_hash", ""))
        config_hash = str(ingest_manifest.get("config_hash", ""))
        artifacts = [
            str(path)
            for path in entity_paths + claim_paths + ner_link_paths + markdown_link_paths
        ]
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="extract",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
            warnings=stage_warnings,
            wall_clock_started_at=_wall_clock_started_at,
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
            "duration_ms": int((time.monotonic() - _start) * 1000),
        }
        append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        detail = {
            "manifest": str(manifest_path),
            "profile": config.active_profile(),
            "run_id": resolved,
        }
        # Spec-028 FR-018: live StageResult MAY omit warnings when empty.
        if stage_warnings:
            detail["warnings"] = stage_warnings
        return StageResult(stage="extract", status="ok", detail=detail)

    def run_link(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
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
            wall_clock_started_at=_wall_clock_started_at,
        )

        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "link",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
            "duration_ms": int((time.monotonic() - _start) * 1000),
        }
        append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        return StageResult(
            stage="link",
            status="ok",
            detail={"manifest": str(manifest_path), "profile": config.active_profile(), "run_id": resolved},
        )

    def run_index(self, root: Path, config: Config, run_id: str | None = None) -> StageResult:
        _start = time.monotonic()
        from auditgraph.storage.hashing import wall_clock_now as _wc_now
        _wall_clock_started_at = _wc_now()
        pkg_root = profile_pkg_root(root, config)
        resolved = self._resolve_run_id(pkg_root, run_id)
        if not resolved:
            return StageResult(stage="index", status="missing_manifest", detail={"run_id": run_id})

        link_manifest = self._load_stage_manifest(pkg_root, resolved, "link")
        if not link_manifest:
            return StageResult(stage="index", status="missing_manifest", detail={"run_id": resolved})

        entities = load_entities(pkg_root)
        # Materialize once — we need both the count (for the warning
        # threshold check) and the list (for BM25 construction).
        entities_materialized = list(entities)
        bm25_path = build_bm25_index(pkg_root, iter(entities_materialized))
        type_index_paths = build_type_indexes(pkg_root, iter(entities_materialized))
        link_type_index_paths = build_link_type_indexes(pkg_root)
        adjacency_path = build_adjacency_index(pkg_root)

        # Spec-028 US3 FR-017: empty_index warning fires iff ≥1 entities
        # on disk AND the BM25 index ended up empty.
        from auditgraph.pipeline.warnings import warning_empty_index

        stage_warnings: list[dict[str, str]] = []
        entity_count = len(entities_materialized)
        bm25_entries = 0
        if bm25_path.exists():
            bm25_payload = read_json(bm25_path)
            postings = bm25_payload.get("postings") if isinstance(bm25_payload, dict) else None
            if isinstance(postings, dict):
                bm25_entries = len(postings)
            elif isinstance(postings, list):
                bm25_entries = len(postings)
        if entity_count >= 1 and bm25_entries == 0:
            stage_warnings.append(warning_empty_index(entity_count).to_dict())

        outputs_hash = sha256_json({
            "bm25": str(bm25_path),
            "semantic": None,
            "type_indexes": sorted(str(p) for p in type_index_paths.values()),
            "link_type_indexes": sorted(str(p) for p in link_type_index_paths.values()),
            "adjacency": str(adjacency_path),
        })
        inputs_hash = str(link_manifest.get("outputs_hash", ""))
        config_hash = str(link_manifest.get("config_hash", ""))
        artifacts = [str(bm25_path)]
        manifest_path = self._write_stage_manifest(
            pkg_root,
            stage="index",
            run_id=resolved,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            config_hash=config_hash,
            artifacts=artifacts,
            warnings=stage_warnings,
            wall_clock_started_at=_wall_clock_started_at,
        )

        replay_path = pkg_root / "runs" / resolved / "replay-log.jsonl"
        replay_line = {
            "stage": "index",
            "run_id": resolved,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "config_hash": config_hash,
            "duration_ms": int((time.monotonic() - _start) * 1000),
        }
        append_text(replay_path, f"{json.dumps(replay_line, sort_keys=True)}\n")

        detail = {
            "manifest": str(manifest_path),
            "profile": config.active_profile(),
            "run_id": resolved,
        }
        if stage_warnings:
            detail["warnings"] = stage_warnings
        return StageResult(stage="index", status="ok", detail=detail)

    def run_rebuild(
        self,
        root: Path,
        config: Config,
        *,
        allow_redaction_misses: bool = False,
    ) -> StageResult:
        from auditgraph.pipeline.postcondition import (
            PostconditionFailed,
            run_postcondition,
            skipped_result,
        )

        pkg_root = profile_pkg_root(root, config)
        check_latest_manifest_compatibility(pkg_root, ARTIFACT_SCHEMA_VERSION)

        def _attach_postcondition_to_index_manifest(run_id: str | None, block: dict) -> None:
            """Read the index manifest, merge the postcondition block, write it back."""
            if not run_id:
                return
            manifest_path = pkg_root / "runs" / run_id / "index-manifest.json"
            if not manifest_path.exists():
                return
            data = read_json(manifest_path)
            data["redaction_postcondition"] = block
            write_json(manifest_path, data)

        run_id: str | None = None
        try:
            ingest = self.run_ingest(root=root, config=config, enforce_compatibility=False)
            if ingest.status != "ok":
                return ingest
            manifest_path = Path(str(ingest.detail.get("manifest", "")))
            run_id = manifest_path.parent.name if manifest_path.exists() else None
            git_prov = self.run_git_provenance(root=root, config=config, run_id=run_id)
            if git_prov.status not in ("ok", "skipped"):
                return git_prov
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

            # Spec 027 FR-024..FR-028: redaction postcondition
            profile_root = profile_pkg_root(root, config)
            postcondition_block = run_postcondition(
                profile_root,
                profile=config.active_profile(),
                config=config,
                allow_misses=allow_redaction_misses,
                raise_on_fail=True,
            )
            _attach_postcondition_to_index_manifest(run_id, postcondition_block)
            return StageResult(
                stage="rebuild",
                status="ok",
                detail={
                    "run_id": run_id,
                    "manifest": index.detail.get("manifest"),
                    "redaction_postcondition": postcondition_block,
                },
            )
        except PostconditionFailed as exc:
            _attach_postcondition_to_index_manifest(run_id, exc.result)
            raise
        except Exception:
            # Any earlier-stage failure: write a `skipped` postcondition
            # entry to the index manifest if it exists, so consumers can
            # tell "didn't run" from "passed".
            _attach_postcondition_to_index_manifest(run_id, skipped_result())
            raise

    def run_import(self, root: Path, config: Config, targets: list[str]) -> StageResult:
        from auditgraph.storage.hashing import wall_clock_now as _wc_now_import
        _wall_clock_started_at = _wc_now_import()
        profile = config.profile()
        policy = load_policy(profile)
        exclude_globs = profile.get("exclude_globs", [])
        import_result = split_imported_with_refusals(root, targets, exclude_globs, policy)
        allowed = import_result.allowed
        skipped = import_result.skipped
        refused_symlinks = import_result.refused_symlinks
        pkg_root = profile_pkg_root(root, config)
        records = []
        # SECURITY: `run_import` previously wrote sources/, documents/,
        # segments/, and chunks/ with plain `write_json`, bypassing the
        # redactor entirely. That meant `auditgraph import <path>` was
        # even worse than `run_ingest` for credential leakage — not a
        # single artifact was scrubbed. Build the same redactor
        # `run_ingest` uses and route every write through it. See
        # specs/026-security-hardening/NOTES.md finding C1.
        redactor = build_redactor(root, config)
        ingest_cfg = profile.get("ingestion", {}) if isinstance(profile, dict) else {}
        parse_options = {
            "ocr_mode": ingest_cfg.get("ocr_mode", "off"),
            "chunk_tokens": int(ingest_cfg.get("chunk_tokens", 200)),
            "chunk_overlap_tokens": int(ingest_cfg.get("chunk_overlap_tokens", 40)),
            "max_file_size_bytes": int(ingest_cfg.get("max_file_size_bytes", 209715200)),
            "ingest_config_hash": ingestion_config_hash(config),
            # Spec 027 FR-016: parser-entry redaction (see parsers.py).
            "redactor": redactor,
        }
        for path in allowed:
            source_hash = sha256_file(path)
            document_id = deterministic_document_id(path.as_posix(), source_hash)
            existing_document_path = pkg_root / "documents" / f"{document_id}.json"
            if existing_document_path.exists():
                existing_document = read_json(existing_document_path)
                if str(existing_document.get("source_hash", "")) == source_hash:
                    # Spec-028 FR-016b1 cache-completeness check (parallel with
                    # run_ingest): pre-028 markdown records lack `text`. Fall
                    # through to fresh parse once to populate it; then takes
                    # the normal cache path on subsequent runs.
                    if _markdown_document_is_complete(existing_document):
                        # Spec-028 FR-001/FR-002 (BUG-1 fix): cache hit ⇒
                        # parse_status="ok", source_origin="cached".
                        record, metadata = build_source_record(
                            path,
                            root,
                            parser_id_for(path),
                            "ok",
                            status_reason=SKIP_REASON_UNCHANGED,
                            skip_reason=SKIP_REASON_UNCHANGED,
                            source_origin="cached",
                        )
                        records.append(record)
                        source_path = pkg_root / "sources" / f"{record.source_hash}.json"
                        # Spec-028 regression fix (parallel with run_ingest):
                        # preserve rich source metadata (frontmatter, document,
                        # segments, chunks) from the previous fresh parse.
                        if source_path.exists():
                            try:
                                existing_meta = read_json(source_path)
                            except Exception:
                                existing_meta = None
                            if isinstance(existing_meta, dict):
                                merged = dict(existing_meta)
                                merged.update(metadata)
                                metadata = merged
                        write_json_redacted(source_path, metadata, redactor)
                        continue
                    # else: fall through to fresh-parse branch below.

            parse_options["source_hash"] = source_hash
            result = parse_file(path, policy, parse_options)
            record, metadata = build_source_record(
                path,
                root,
                result.parser_id,
                result.status,
                status_reason=result.status_reason,
                skip_reason=result.skip_reason,
                extra_metadata=result.metadata,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json_redacted(source_path, metadata, redactor)

            document_payload = metadata.get("document") if isinstance(metadata, dict) else None
            segments_payload = metadata.get("segments") if isinstance(metadata, dict) else None
            chunks_payload = metadata.get("chunks") if isinstance(metadata, dict) else None
            if isinstance(document_payload, dict) and isinstance(segments_payload, list) and isinstance(chunks_payload, list):
                # SECURITY (Spec 027 FR-016): payloads are already redacted by
                # the parser entry point (see auditgraph/ingest/parsers.py).
                write_document_artifacts(
                    pkg_root,
                    document_payload,
                    segments_payload,
                    chunks_payload,
                )

        for path in skipped:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                status_reason=SKIP_REASON_UNSUPPORTED,
                skip_reason=SKIP_REASON_UNSUPPORTED,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json_redacted(source_path, metadata, redactor)

        # Spec 027 FR-001..FR-004: refused symlinks surface as skipped sources
        # under run_import as well, with the same skip reason as run_ingest.
        for path in refused_symlinks:
            record, metadata = build_source_record(
                path,
                root,
                "text/unknown",
                "skipped",
                status_reason=SKIP_REASON_SYMLINK_REFUSED,
                skip_reason=SKIP_REASON_SYMLINK_REFUSED,
            )
            records.append(record)
            source_path = pkg_root / "sources" / f"{record.source_hash}.json"
            write_json_redacted(source_path, metadata, redactor)

        # Spec 027 FR-002: one-line stderr warning on refusal.
        if refused_symlinks:
            sys.stderr.write(
                f"WARN: refused {len(refused_symlinks)} symlinks pointing outside "
                f"{root.resolve()} (see manifest for details)\n"
            )

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
        from auditgraph.storage.hashing import wall_clock_now

        # Spec-028 US6 (BUG-3 fix): wall_clock_started_at was captured at
        # stage entry (near the top of run_ingest / run_import). Capture
        # wall_clock_finished_at now, right before we build the manifest
        # so the pair reflects actual stage duration.
        _wall_clock_finished_at = wall_clock_now()
        manifest = build_manifest(
            run_id=run_id,
            started_at=self._deterministic_time_for(run_id),
            finished_at=self._deterministic_time_for(run_id),
            wall_clock_started_at=_wall_clock_started_at,
            wall_clock_finished_at=_wall_clock_finished_at,
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
                "ok": sum(1 for record in records if record.parse_status == "ok"),
                "skipped": sum(1 for record in records if record.parse_status == "skipped"),
                "failed": sum(1 for record in records if record.parse_status == "failed"),
            },
        )

