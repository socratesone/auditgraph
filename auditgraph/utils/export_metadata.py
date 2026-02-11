from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from auditgraph.config import Config
from auditgraph.storage.hashing import sha256_text
from auditgraph.utils.redaction import RedactionPolicy, RedactionSummary


def build_export_metadata(
    root: Path,
    config: Config,
    policy: RedactionPolicy,
    summary: RedactionSummary,
) -> dict[str, object]:
    root_id = sha256_text(str(root.resolve()))
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "created_at": created_at,
        "profile": config.active_profile(),
        "root_id": root_id,
        "redaction_policy_id": policy.policy_id,
        "redaction_policy_version": policy.version,
        "redaction_summary": summary.to_dict(),
        "clean_room": policy.enabled,
    }
