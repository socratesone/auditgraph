from __future__ import annotations

from pathlib import Path

from auditgraph.normalize.paths import normalize_path


SUPPORTED_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx"}


def extract_code_symbols(root: Path, paths: list[Path]) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []
    for path in paths:
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        normalized = normalize_path(path, root=root)
        symbols.append(
            {
                "type": "file",
                "name": path.name,
                "canonical_key": f"file:{normalized}",
                "source_path": normalized,
            }
        )
    return symbols
