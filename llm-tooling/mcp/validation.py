"""MCP payload validation layer (Spec 027 User Story 2).

This module sits between the MCP transport (`server.py:execute_tool`) and
the CLI subprocess dispatch. Every incoming tool-call payload is validated
against the target tool's declared `input_schema` before any argv
construction happens. Validation failures return a structured error
envelope and never invoke a subprocess.

Implementation notes:

- The validator is backed by `jsonschema` (Draft 7-compatible by default).
  `jsonschema>=4,<5` is pinned in `pyproject.toml`.
- String parameters without an explicit `maxLength` inherit a server-level
  default (`DEFAULT_MAX_STRING_LENGTH`) per Spec 027 FR-007.
- The default is overridable via `AUDITGRAPH_MCP_MAX_STRING_LENGTH` env var
  (see `resolve_max_string_length`). Zero, negative, or non-numeric values
  raise `ConfigurationError` at validation time (not at module import) so
  tests can use `monkeypatch.setenv`.
- Error envelopes NEVER echo the rejected value to avoid reflecting
  adversarial input into operator logs (see `contracts/mcp-validation-errors.md`).
"""
from __future__ import annotations

import os
from typing import Any


DEFAULT_MAX_STRING_LENGTH = 4096
_MAX_STRING_LENGTH_ENV_VAR = "AUDITGRAPH_MCP_MAX_STRING_LENGTH"


class ConfigurationError(ValueError):
    """Raised when a server-level configuration value is invalid."""


class ValidationFailed(Exception):
    """Raised by `validate` when an incoming payload violates the tool schema.

    Carries the structured envelope fields so `execute_tool` can translate
    to the on-the-wire error shape without re-inspecting the exception.

    NOTE: plain class (not @dataclass) because this module is sometimes
    loaded via `importlib.util.spec_from_file_location`, which doesn't
    register the synthetic module name in `sys.modules` — `@dataclass`
    then fails to introspect the module's namespace.
    """

    def __init__(self, *, tool_name: str = "", field: str = "", reason: str = "") -> None:
        self.tool_name = tool_name
        self.field = field
        self.reason = reason
        super().__init__(f"validation_failed in tool {tool_name}: {reason}")

    def to_envelope(self) -> dict:
        return {
            "error": {
                "code": "validation_failed",
                "tool": self.tool_name,
                "field": self.field,
                "reason": self.reason,
            }
        }


def resolve_max_string_length() -> int:
    """Return the effective server-level string length cap.

    Reads `AUDITGRAPH_MCP_MAX_STRING_LENGTH` from the environment. If
    unset, returns `DEFAULT_MAX_STRING_LENGTH`. If set to a zero, negative,
    or non-numeric value, raises `ConfigurationError` with a sanitized
    message (the raw env var value is NOT echoed — an attacker who can
    set environment variables could otherwise plant adversarial content
    in operator logs via the error message).
    """
    raw = os.environ.get(_MAX_STRING_LENGTH_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_STRING_LENGTH
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ConfigurationError(
            f"{_MAX_STRING_LENGTH_ENV_VAR} must be a positive integer "
            f"(got a non-numeric value of length {len(raw) if raw is not None else 0})"
        )
    if value <= 0:
        raise ConfigurationError(
            f"{_MAX_STRING_LENGTH_ENV_VAR} must be a positive integer "
            f"(got {value}); the cap cannot be disabled"
        )
    return value


# ---------------------------------------------------------------------------
# Validation entry point
# ---------------------------------------------------------------------------


def validate(tool_schema: dict, payload: Any, *, tool_name: str) -> None:
    """Validate ``payload`` against ``tool_schema``.

    Raises ``ValidationFailed`` on any violation. Returns ``None`` on success.

    This is a stub during Phase 2 Foundational; the real implementation
    lands in Phase 4 User Story 2 (tasks T029-T034 + T035b).
    """
    # Phase 2 skeleton: accept any payload. Real validation lands in Phase 4.
    # The skeleton tests only verify the symbol exists and is callable.
    _ = tool_schema, payload, tool_name
    return None
