from __future__ import annotations

from typing import Iterable


FRONTMATTER_FIELDS = {"title", "tags", "project", "status"}


def _parse_kv_line(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value


def _parse_tags(value: str) -> list[str]:
    value = value.strip().strip("[]")
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_frontmatter(lines: Iterable[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    for line in lines:
        parsed = _parse_kv_line(line)
        if not parsed:
            continue
        key, value = parsed
        if key not in FRONTMATTER_FIELDS:
            continue
        if key == "tags":
            data[key] = _parse_tags(value)
        else:
            data[key] = value
    return data


def extract_frontmatter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return {}

    frontmatter_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter_lines.append(line)
    return parse_frontmatter(frontmatter_lines)
