from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from auditgraph.storage.artifacts import read_json, write_json


@dataclass(frozen=True)
class ProvenanceRecord:
    artifact_id: str
    source_path: str
    source_hash: str
    rule_id: str
    input_hash: str
    run_id: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def write_provenance_index(pkg_root: Path, run_id: str, records: Iterable[ProvenanceRecord]) -> Path:
    path = pkg_root / "provenance" / f"{run_id}.json"
    existing: list[dict[str, object]] = []
    if path.exists():
        existing = list(read_json(path))
    payload = existing + [record.to_dict() for record in records]
    write_json(path, payload)
    return path
