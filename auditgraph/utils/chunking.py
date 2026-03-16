from __future__ import annotations

from typing import Any


def tokenize(text: str) -> list[str]:
    return [token for token in text.split() if token]


def chunk_tokens(tokens: list[str], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[dict[str, Any]] = []
    step = chunk_size - overlap
    index = 0
    while index < len(tokens):
        window = tokens[index : index + chunk_size]
        if not window:
            break
        chunks.append(
            {
                "start": index,
                "end": index + len(window),
                "overlap": overlap if chunks else 0,
                "tokens": window,
            }
        )
        if index + chunk_size >= len(tokens):
            break
        index += step
    return chunks


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    tokens = tokenize(text)
    windows = chunk_tokens(tokens, chunk_size, overlap)
    chunks: list[dict[str, Any]] = []
    for window in windows:
        raw_values = window.get("tokens")
        values = [str(value) for value in raw_values] if isinstance(raw_values, list) else []
        raw_start = window.get("start", 0)
        raw_end = window.get("end", 0)
        raw_overlap = window.get("overlap", 0)
        start = int(raw_start) if isinstance(raw_start, int) else 0
        end = int(raw_end) if isinstance(raw_end, int) else 0
        overlap_tokens = int(raw_overlap) if isinstance(raw_overlap, int) else 0
        chunks.append(
            {
                "text": " ".join(values),
                "token_count": len(values),
                "start": start,
                "end": end,
                "overlap_tokens": overlap_tokens,
            }
        )
    return chunks
