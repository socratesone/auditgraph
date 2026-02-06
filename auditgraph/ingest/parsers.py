from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auditgraph.ingest.frontmatter import extract_frontmatter
from auditgraph.ingest.policy import SKIP_REASON_UNSUPPORTED, IngestionPolicy, is_allowed, parser_id_for


@dataclass(frozen=True)
class ParseResult:
    parser_id: str
    status: str
    text: str
    skip_reason: str | None = None
    metadata: dict[str, object] | None = None


def parse_file(path: Path, policy: IngestionPolicy) -> ParseResult:
    if not is_allowed(path, policy):
        return ParseResult(
            parser_id="text/unknown",
            status="skipped",
            text="",
            skip_reason=SKIP_REASON_UNSUPPORTED,
        )

    parser_id = parser_id_for(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, object] = {}
    if parser_id == "text/markdown":
        metadata["frontmatter"] = extract_frontmatter(text)
    return ParseResult(parser_id=parser_id, status="ok", text=text, metadata=metadata)
