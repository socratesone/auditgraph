from __future__ import annotations

from pathlib import Path
from typing import Iterable

from auditgraph.extract.adr import extract_decisions
from auditgraph.extract.entities import build_log_claim
from auditgraph.extract.logs import extract_log_signatures
from auditgraph.index.decisions import write_decision_index
from auditgraph.storage.artifacts import write_json


def _shard_dir(root: Path, identifier: str) -> Path:
    token = identifier.split("_", 1)[-1]
    shard = token[:2] if token else identifier[:2]
    return root / shard


def write_entities(pkg_root: Path, entities: Iterable[dict[str, object]]) -> list[Path]:
    paths: list[Path] = []
    for entity in entities:
        entity_id = entity["id"]
        shard = _shard_dir(pkg_root / "entities", entity_id)
        path = shard / f"{entity_id}.json"
        write_json(path, entity)
        paths.append(path)
    return paths


def write_claims(pkg_root: Path, claims: Iterable[dict[str, object]]) -> list[Path]:
    paths: list[Path] = []
    for claim in claims:
        claim_id = claim["id"]
        shard = _shard_dir(pkg_root / "claims", claim_id)
        path = shard / f"{claim_id}.json"
        write_json(path, claim)
        paths.append(path)
    return paths


def write_extract_manifest(pkg_root: Path, run_id: str, entities: list[dict[str, object]], claims: list[dict[str, object]]) -> Path:
    manifest = {
        "run_id": run_id,
        "entities": len(entities),
        "claims": len(claims),
        "artifacts": {
            "entities": [str(p) for p in write_entities(pkg_root, entities)],
            "claims": [str(p) for p in write_claims(pkg_root, claims)],
        },
    }
    manifest_path = pkg_root / "runs" / run_id / "extract-manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def extract_adr_claims(pkg_root: Path, paths: Iterable[Path]) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    for path in paths:
        claims.extend(extract_decisions(path))
    if claims:
        write_decision_index(pkg_root, claims)
    return claims


def extract_log_claims(paths: Iterable[Path]) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    for path in paths:
        for signature in extract_log_signatures(path):
            claims.append(build_log_claim(signature))
    return claims
