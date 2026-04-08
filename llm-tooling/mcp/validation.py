"""MCP payload validation layer (Spec 027 User Story 2).

This module sits between the MCP transport (`server.py:execute_tool`) and
the CLI subprocess dispatch. Every incoming tool-call payload is validated
against the target tool's declared `input_schema` before any argv
construction happens. Validation failures return a structured error
envelope and never invoke a subprocess.

Implementation notes:

- The validator is backed by `jsonschema` (Draft 7-compatible).
- String parameters without an explicit `maxLength` inherit a server-level
  default (`DEFAULT_MAX_STRING_LENGTH`) per Spec 027 FR-007.
- The default is overridable via `AUDITGRAPH_MCP_MAX_STRING_LENGTH` env var
  (see `resolve_max_string_length`). Zero, negative, or non-numeric values
  raise `ConfigurationError` at validation time (not at module import) so
  tests can use `monkeypatch.setenv`.
- Error envelopes NEVER echo the rejected value (see
  `contracts/mcp-validation-errors.md`).
"""
from __future__ import annotations

import copy
import os
from typing import Any


DEFAULT_MAX_STRING_LENGTH = 4096
_MAX_STRING_LENGTH_ENV_VAR = "AUDITGRAPH_MCP_MAX_STRING_LENGTH"


class ConfigurationError(ValueError):
    """Raised when a server-level configuration value is invalid."""


class ValidationFailed(Exception):
    """Raised by `validate` when an incoming payload violates the tool schema.

    Plain class (not @dataclass) because this module is sometimes loaded via
    `importlib.util.spec_from_file_location`, which doesn't register the
    synthetic module name in `sys.modules` — `@dataclass` then fails to
    introspect the module's namespace.
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

    Reads `AUDITGRAPH_MCP_MAX_STRING_LENGTH` from the environment. If unset,
    returns `DEFAULT_MAX_STRING_LENGTH`. Zero, negative, or non-numeric
    values raise `ConfigurationError` with a sanitized message.
    """
    raw = os.environ.get(_MAX_STRING_LENGTH_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_STRING_LENGTH
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ConfigurationError(
            f"{_MAX_STRING_LENGTH_ENV_VAR} must be a positive integer "
            f"(got a non-numeric value of length {len(raw)})"
        )
    if value <= 0:
        raise ConfigurationError(
            f"{_MAX_STRING_LENGTH_ENV_VAR} must be a positive integer "
            f"(got {value}); the cap cannot be disabled"
        )
    return value


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _apply_default_max_length(schema: dict, default_cap: int) -> dict:
    """Return a deep copy of ``schema`` with ``maxLength`` filled in on every
    string property that lacks an explicit cap. The default cap suffix
    "(server default)" is NOT added here — the translation layer detects
    whether the violated cap was the default or an explicit one by
    comparing the validator_value.
    """
    patched = copy.deepcopy(schema)
    _walk_apply_default(patched, default_cap)
    return patched


def _walk_apply_default(node: Any, default_cap: int) -> None:
    if not isinstance(node, dict):
        return
    if node.get("type") == "string" and "maxLength" not in node:
        node["maxLength"] = default_cap
    for key in ("properties", "patternProperties", "definitions", "$defs"):
        sub = node.get(key)
        if isinstance(sub, dict):
            for child in sub.values():
                _walk_apply_default(child, default_cap)
    items = node.get("items")
    if isinstance(items, dict):
        _walk_apply_default(items, default_cap)
    elif isinstance(items, list):
        for child in items:
            _walk_apply_default(child, default_cap)
    for key in ("allOf", "anyOf", "oneOf"):
        arr = node.get(key)
        if isinstance(arr, list):
            for child in arr:
                _walk_apply_default(child, default_cap)


def _field_path(err) -> str:
    """Convert `jsonschema.ValidationError.path` (a deque of path components)
    to a JSON Pointer. Empty deque → "".
    """
    components = list(err.path)
    if not components:
        return ""
    return "/" + "/".join(str(p) for p in components)


def _translate_error(err, tool_name: str, default_cap: int) -> "ValidationFailed":
    """Translate a jsonschema ValidationError into a ValidationFailed.

    Per `contracts/mcp-validation-errors.md`: NEVER interpolate err.instance
    into any reason string.
    """
    validator = getattr(err, "validator", None)
    validator_value = getattr(err, "validator_value", None)
    field = _field_path(err)

    if validator == "type":
        actual_type = type(err.instance).__name__
        reason = f"expected {validator_value}, got {actual_type}"
    elif validator == "required":
        # err.validator_value is the list of required properties; the missing
        # one is the first that isn't present in err.instance.
        missing = ""
        if isinstance(err.instance, dict) and isinstance(validator_value, list):
            for name in validator_value:
                if name not in err.instance:
                    missing = name
                    break
        reason = f"required property {missing} missing"
    elif validator == "additionalProperties":
        # Derive the first unknown key from the instance vs schema diff.
        unknown_name = ""
        if isinstance(err.instance, dict):
            schema_props = set()
            if isinstance(err.schema, dict):
                schema_props = set(err.schema.get("properties", {}).keys())
            extras = sorted(set(err.instance.keys()) - schema_props)
            if extras:
                unknown_name = extras[0]
        reason = f"unknown property {unknown_name}".rstrip()
    elif validator == "maxLength":
        if validator_value == default_cap:
            reason = f"exceeds maxLength of {validator_value} (server default)"
        else:
            reason = f"exceeds maxLength of {validator_value}"
    elif validator == "minLength":
        reason = f"below minLength of {validator_value}"
    elif validator == "maximum":
        reason = f"exceeds maximum of {validator_value}"
    elif validator == "minimum":
        reason = f"below minimum of {validator_value}"
    elif validator == "enum":
        try:
            sorted_values = sorted(validator_value)
        except TypeError:
            sorted_values = list(validator_value) if validator_value is not None else []
        reason = f"value not in enum {sorted_values}"
    elif validator == "pattern":
        reason = "value does not match required pattern"
    else:
        reason = f"validation failed: {validator}"

    return ValidationFailed(tool_name=tool_name, field=field, reason=reason)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def validate(tool_schema: dict, payload: Any, *, tool_name: str) -> None:
    """Validate ``payload`` against ``tool_schema``.

    Raises ``ValidationFailed`` on any violation. Returns ``None`` on success.
    """
    import jsonschema

    default_cap = resolve_max_string_length()
    patched = _apply_default_max_length(tool_schema or {}, default_cap)
    validator = jsonschema.Draft7Validator(patched)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if not errors:
        return None
    raise _translate_error(errors[0], tool_name, default_cap)
