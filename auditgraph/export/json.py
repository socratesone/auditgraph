from __future__ import annotations

from pathlib import Path

from auditgraph.config import Config, footprint_budget_settings, load_config
from auditgraph.utils.export_metadata import build_export_metadata
from auditgraph.utils.redaction import build_redactor_for_pkg_root
from auditgraph.utils.budget import enforce_budget, evaluate_pkg_budget, latest_source_bytes

from auditgraph.storage.artifacts import write_json
from auditgraph.storage.loaders import load_chunks, load_documents, load_entities


def export_json(root: Path, pkg_root: Path, output_path: Path, config: Config | None = None) -> Path:
    resolved = config or load_config(None)
    budget_settings = footprint_budget_settings(resolved)
    source_bytes = latest_source_bytes(pkg_root)
    budget_status = evaluate_pkg_budget(pkg_root, source_bytes, budget_settings, additional_bytes=0)
    enforce_budget(budget_status)
    redactor = build_redactor_for_pkg_root(pkg_root, resolved)
    data = {
        "entities": load_entities(pkg_root, sorted_by_id=True),
        "documents": load_documents(pkg_root),
        "chunks": load_chunks(pkg_root),
    }
    redaction_result = redactor.redact_payload(data)
    payload = dict(redaction_result.value)
    payload["export_metadata"] = build_export_metadata(
        root,
        resolved,
        redactor.policy,
        redaction_result.summary,
    )
    write_json(output_path, payload)
    return output_path
