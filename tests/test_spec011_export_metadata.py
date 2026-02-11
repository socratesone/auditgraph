from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.export.json import export_json
from auditgraph.storage.artifacts import read_json, write_json
from auditgraph.storage.hashing import sha256_text


SENTINEL = "S011_SECRET_SENTINEL"


def test_export_metadata_includes_redaction_summary(tmp_path: Path) -> None:
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    entity_id = "ent_meta"
    entity = {
        "id": entity_id,
        "type": "file",
        "name": f"token={SENTINEL}",
        "canonical_key": f"file:token={SENTINEL}",
    }
    shard = pkg_root / "entities" / "me"
    shard.mkdir(parents=True, exist_ok=True)
    write_json(shard / f"{entity_id}.json", entity)

    output_path = tmp_path / "exports" / "subgraphs" / "export.json"
    config = load_config(None)
    export_json(tmp_path, pkg_root, output_path, config=config)

    payload = read_json(output_path)
    metadata = payload.get("export_metadata")

    assert isinstance(metadata, dict)
    assert metadata.get("clean_room") is True
    assert metadata.get("profile") == "default"
    assert metadata.get("root_id") == sha256_text(str(tmp_path.resolve()))
    assert metadata.get("redaction_policy_id") == "redaction.policy.v1"
    assert metadata.get("redaction_policy_version") == "v1"

    summary = metadata.get("redaction_summary")
    assert isinstance(summary, dict)
    assert summary.get("total_matches") == 2
    assert summary.get("counts_by_category", {}).get("credential") == 2
