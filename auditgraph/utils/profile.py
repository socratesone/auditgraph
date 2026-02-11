from __future__ import annotations

from auditgraph.errors import SecurityPolicyError


def validate_profile_name(name: str) -> str:
    value = str(name)
    if not value or not value.strip():
        raise SecurityPolicyError("Profile name must not be empty")
    if "/" in value or "\\" in value:
        raise SecurityPolicyError("Profile name must not contain path separators")
    if ".." in value:
        raise SecurityPolicyError("Profile name must not contain '..'")
    return value
