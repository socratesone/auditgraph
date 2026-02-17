from __future__ import annotations

from pathlib import Path

from auditgraph.storage.artifacts import write_json


def _entity_path(pkg_root: Path, entity_id: str) -> Path:
    token = entity_id.split("_", 1)[-1]
    shard = token[:2] if token else entity_id[:2]
    return pkg_root / "entities" / shard / f"{entity_id}.json"


def _link_path(pkg_root: Path, link_id: str) -> Path:
    token = link_id.split("_", 1)[-1]
    shard = token[:2] if token else link_id[:2]
    return pkg_root / "links" / shard / f"{link_id}.json"


def write_test_graph(pkg_root: Path) -> tuple[list[str], list[str]]:
    entity_a = {
        "id": "ent_bb01",
        "type": "note",
        "name": "Token=abc123",
        "canonical_key": "note:bb01",
        "refs": [{"source_path": "notes/a.md", "source_hash": "h1"}],
    }
    entity_b = {
        "id": "ent_aa01",
        "type": "task",
        "name": "Build feature",
        "canonical_key": "task:aa01",
        "refs": [{"source_path": "notes/b.md", "source_hash": "h2"}],
    }
    link = {
        "id": "lnk_1001",
        "from_id": "ent_aa01",
        "to_id": "ent_bb01",
        "type": "mentions",
        "rule_id": "link.source_cooccurrence.v1",
        "confidence": 1.0,
        "authority": "authoritative",
        "evidence": [{"source_path": "notes/a.md", "source_hash": "h1"}],
    }

    write_json(_entity_path(pkg_root, entity_a["id"]), entity_a)
    write_json(_entity_path(pkg_root, entity_b["id"]), entity_b)
    write_json(_link_path(pkg_root, link["id"]), link)
    return ([entity_a["id"], entity_b["id"]], [link["id"]])
