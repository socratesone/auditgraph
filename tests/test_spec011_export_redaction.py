from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.export.json import export_json
from auditgraph.storage.artifacts import read_json, write_json


SENTINEL = "S011_SECRET_SENTINEL"


def test_export_redacts_entity_fields(tmp_path: Path) -> None:
    pkg_root = tmp_path / ".pkg" / "profiles" / "default"
    entity_id = "ent_test"
    entity = {
        "id": entity_id,
        "type": "file",
        "name": f"token={SENTINEL}",
        "canonical_key": f"file:token={SENTINEL}",
    }
    shard = pkg_root / "entities" / "te"
    shard.mkdir(parents=True, exist_ok=True)
    write_json(shard / f"{entity_id}.json", entity)

    output_path = tmp_path / "exports" / "subgraphs" / "export.json"
    export_json(tmp_path, pkg_root, output_path, config=load_config(None))

    payload = read_json(output_path)
    serialized = str(payload)
    assert SENTINEL not in serialized
