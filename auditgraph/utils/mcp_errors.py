"""Normalized error codes and helpers for MCP tooling."""

ERROR_CODES = (
    "INVALID_INPUT",
    "NOT_FOUND",
    "CONFLICT",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "TIMEOUT",
    "RATE_LIMITED",
    "UPSTREAM_ERROR",
    "INTERNAL_ERROR",
)


def normalize_error(code: str, message: str, *, detail: str | None = None) -> dict[str, str]:
    """Return a normalized error payload with a safe fallback code."""
    normalized = code if code in ERROR_CODES else "INTERNAL_ERROR"
    payload = {"code": normalized, "message": message}
    if detail:
        payload["detail"] = detail
    return payload
