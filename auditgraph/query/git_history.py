"""git_history: Full provenance summary for a file.

Composes git_who + git_log + git_introduced into a single response.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auditgraph.query.git_introduced import git_introduced
from auditgraph.query.git_log import git_log
from auditgraph.query.git_who import git_who


def git_history(pkg_root: Path, file_path: str) -> dict[str, Any]:
    """Return combined provenance summary for the given file.

    Returns:
        {"status": "ok", "file": file_path, "authors": [...], "commits": [...],
         "introduced": {...}, "lineage": [...]}
        or {"status": "error", "message": "..."}
    """
    who_result = git_who(pkg_root, file_path)
    if who_result["status"] == "error":
        return who_result

    log_result = git_log(pkg_root, file_path)
    if log_result["status"] == "error":
        return log_result

    intro_result = git_introduced(pkg_root, file_path)
    if intro_result["status"] == "error":
        return intro_result

    return {
        "status": "ok",
        "file": file_path,
        "authors": who_result["authors"],
        "commits": log_result["commits"],
        "introduced": intro_result["commit"],
        "lineage": intro_result["lineage"],
    }
