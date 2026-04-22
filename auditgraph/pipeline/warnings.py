"""Spec-028 US3 · Structured throughput warnings.

Binary threshold (FR-017): a warning fires iff the stage received ≥1
input from the prior stage AND produced exactly 0 output. No ratio
thresholds, no tuning — a clean, testable boundary.

Warnings live in two places per `contracts/stage-manifest-warnings.md`:
- Live `StageResult.detail["warnings"]` — MAY be omitted when empty.
- Persisted stage manifest top-level `warnings` key — ALWAYS serialized
  as a list (even `[]`), giving operators a stable JSON path.

Neither representation participates in `outputs_hash` (Invariant I7).
"""
from __future__ import annotations

from dataclasses import dataclass

# Authoritative warning codes (stable strings — grep for them in CI / audits).
THROUGHPUT_WARNING_NO_ENTITIES = "no_entities_produced"
THROUGHPUT_WARNING_EMPTY_INDEX = "empty_index"


@dataclass(frozen=True)
class ThroughputWarning:
    """Structured advisory emitted by a pipeline stage when throughput is
    unexpectedly empty given nonzero input.

    The dict shape returned by ``to_dict`` is what lands in
    ``StageResult.detail["warnings"]`` and in the persisted manifest.
    """

    code: str
    message: str
    hint: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


def warning_no_entities(upstream_inputs: int) -> ThroughputWarning:
    """Return a no_entities_produced warning sized to the upstream input count.

    Fires from ``run_extract`` when the stage completed successfully but
    emitted zero entities while receiving at least one ingested source.
    """
    return ThroughputWarning(
        code=THROUGHPUT_WARNING_NO_ENTITIES,
        message=f"extract produced 0 entities from {upstream_inputs} ingested file(s)",
        hint=(
            "Check that at least one extractor is active for the ingested file types. "
            "For markdown corpora, verify `extraction.markdown.enabled: true` in your "
            "profile config. For log corpora, verify `extraction.rule_packs` resolves "
            "to readable rule files."
        ),
    )


def warning_empty_index(entity_count: int) -> ThroughputWarning:
    """Return an empty_index warning.

    Fires from ``run_index`` when the BM25 index ends up empty despite a
    nonzero entity count on disk.
    """
    return ThroughputWarning(
        code=THROUGHPUT_WARNING_EMPTY_INDEX,
        message=f"index is empty despite {entity_count} entities on disk",
        hint=(
            "Re-run `auditgraph rebuild` from a clean state, or inspect "
            "`.pkg/profiles/<profile>/indexes/bm25/index.json` for corruption."
        ),
    )
