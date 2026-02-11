from __future__ import annotations

from pathlib import Path

from auditgraph.config import Config, load_config
from auditgraph.utils.export_metadata import build_export_metadata
from auditgraph.utils.redaction import build_redactor_for_pkg_root

from auditgraph.storage.artifacts import read_json, write_json


def _load_entities(pkg_root: Path) -> list[dict[str, object]]:
    entities_dir = pkg_root / "entities"
    entities: list[dict[str, object]] = []
    if not entities_dir.exists():
        return entities
    for path in entities_dir.rglob("*.json"):
        entities.append(read_json(path))
    return sorted(entities, key=lambda item: str(item.get("id", "")))


def export_json(root: Path, pkg_root: Path, output_path: Path, config: Config | None = None) -> Path:
    resolved = config or load_config(None)
    redactor = build_redactor_for_pkg_root(pkg_root, resolved)
    data = {
        "entities": _load_entities(pkg_root),
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
