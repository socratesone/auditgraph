# Contract: MCP validation error envelope

Defines the exact error shape returned by `llm-tooling/mcp/server.py:execute_tool` when `llm-tooling/mcp/validation.py:validate` rejects an incoming tool-call payload against the target tool's `input_schema`, and the specific translation rules from `jsonschema.ValidationError` to the project's structured envelope.

Applies to: User Story 2 / FR-005 through FR-009 / Clarification Q4.

## Envelope shape

```json
{
  "error": {
    "code": "validation_failed",
    "tool": "<tool_name>",
    "field": "<json_pointer>",
    "reason": "<human_readable_message>"
  }
}
```

This replaces (not augments) the successful result dict. Callers distinguish success from validation failure by checking `"error" in result`.

## Field-by-field constraints

### `error.code`

- Always literal string `"validation_failed"` for this error class.
- Distinct from other MCP error codes produced by `execute_tool`: `"forbidden"` (read-only mode rejection), `"timeout"` (subprocess timeout), `"subprocess_failed"` (non-zero exit from the dispatched CLI), `"not_found"` (unknown tool name).
- Future error classes MUST use distinct string values; `"validation_failed"` is reserved for schema violations produced by the validator.

### `error.tool`

- Non-empty string.
- Matches the `name` field from the tool entry in `llm-tooling/tool.manifest.json`.
- Used by callers to correlate the error with their outbound request.

### `error.field`

- JSON Pointer (RFC 6901) identifying the location of the violation within the submitted payload.
- Empty string `""` means the whole payload (e.g., "payload is not an object").
- `/q` means the top-level `q` property.
- `/filters/0/op` means the `op` field of the first element of the `filters` array.
- Always derived from `jsonschema.ValidationError.path` via `"/" + "/".join(str(p) for p in error.path)` (empty deque → `""`).
- Numeric path components (array indices) are serialized as-is without leading zeros.

### `error.reason`

- Human-readable string.
- MUST NOT include the rejected value or any portion of the payload. The reason describes *what was wrong* without echoing *what was submitted*.
- MUST be deterministic for a given validator error type — the same violation produces the same reason string, so callers can dispatch on it if needed.
- Short enough to fit in a single log line (target ≤ 200 characters).

## What MUST NOT appear anywhere in the envelope

1. **The rejected value.** A payload like `{"q": "A" * 10000}` produces `"exceeds maxLength of 1024"`, never `"exceeds maxLength of 1024: AAAAAA..."`.
2. **Stack traces.** `jsonschema.ValidationError.__str__()` includes context that often has the full instance. The translation layer MUST use `err.message` and `err.validator` / `err.validator_value`, never `str(err)`.
3. **Internal state.** No paths to the server's own files, no memory addresses, no timing metrics.
4. **Schema paths.** `jsonschema.ValidationError.schema_path` is an internal implementation detail; callers should not learn where in the schema definition the rule lives.

## Translation rules (`jsonschema.ValidationError` → envelope)

The translation is implemented by `llm-tooling/mcp/validation.py:_translate_error(err)` as a pure function mapping `jsonschema.ValidationError` to the envelope dict. The mapping is deterministic and does not depend on jsonschema library version (within the `>=4,<5` pin).

### Per-validator reason templates

| `err.validator` | Reason template |
|---|---|
| `"type"` | `"expected {validator_value}, got {actual_type}"` where `{actual_type}` is derived from `type(err.instance).__name__` — but the instance itself is NOT interpolated |
| `"required"` | `"required property {missing} missing"` — `{missing}` is the first missing property name from `err.validator_value` |
| `"additionalProperties"` | `"unknown property {name}"` — `{name}` is the first extra property name derived from `set(err.instance.keys()) - set(err.schema.get("properties", {}).keys())` |
| `"maxLength"` | `"exceeds maxLength of {validator_value}"` |
| `"minLength"` | `"below minLength of {validator_value}"` |
| `"maximum"` | `"exceeds maximum of {validator_value}"` |
| `"minimum"` | `"below minimum of {validator_value}"` |
| `"enum"` | `"value not in enum {sorted_validator_value}"` — enum list is sorted for deterministic output but the rejected value is not shown |
| `"pattern"` | `"value does not match required pattern"` — pattern itself is NOT echoed (could be adversarially-crafted ReDoS seed) |
| any other | `"validation failed: {validator}"` — generic fallback |

**Critical rule**: every template above inserts only `validator_value` (the schema constraint, known-safe) or derived metadata (missing property name, actual type name). **None** interpolate `err.instance` directly.

### Example translations

**Input payload**: `{"q": 42}` against schema `{"properties": {"q": {"type": "string"}}}`

```json
{
  "error": {
    "code": "validation_failed",
    "tool": "ag_query",
    "field": "/q",
    "reason": "expected string, got int"
  }
}
```

**Input payload**: `{"q": "hello", "malicious": "payload"}` against schema with `"additionalProperties": false`

```json
{
  "error": {
    "code": "validation_failed",
    "tool": "ag_query",
    "field": "",
    "reason": "unknown property malicious"
  }
}
```

**Input payload**: `{"q": "A" * 5000}` against schema `{"properties": {"q": {"maxLength": 1024}}}`

```json
{
  "error": {
    "code": "validation_failed",
    "tool": "ag_query",
    "field": "/q",
    "reason": "exceeds maxLength of 1024"
  }
}
```

## Subprocess guarantee

On any validation failure, `execute_tool` MUST return the error envelope **without invoking `adapter.run_command(argv)` or any subprocess**. The failing code path returns before the subprocess call site. This is enforced by a unit test that mocks `subprocess.run` (or `adapter.run_command`) and asserts it was never called when the payload was rejected.

The implementation sketch:

```python
def execute_tool(tool_name: str, payload: dict) -> dict:
    tool = _find_tool(load_manifest(), tool_name)
    try:
        _enforce_read_only(tool)
        # NEW: validation happens here, before any subprocess setup
        validation.validate(tool.get("input_schema", {}), payload, tool_name=tool_name)
    except validation.ValidationFailed as exc:
        return exc.to_envelope()
    except PermissionError:
        return {"error": {"code": "forbidden", "tool": tool_name, "field": "", "reason": "read-only mode"}}
    # ... existing subprocess dispatch path continues here, unchanged ...
```

## Size cap default

Per FR-007, parameters without an explicit `maxLength` in their schema inherit a server-level default. This default is a constant in `llm-tooling/mcp/validation.py`:

```python
DEFAULT_MAX_STRING_LENGTH = 4096
```

- Applied to any string parameter whose schema does NOT declare `maxLength`.
- Applied before the jsonschema validator runs, so the violation is reported with `reason: "exceeds maxLength of 4096 (server default)"`.
- The suffix `"(server default)"` distinguishes default-triggered violations from explicit schema-cap violations, so operators can tell the difference when tuning per-parameter limits.
- The default MUST NOT be zero or negative; the validator raises a configuration error at startup if so. (Guards against a future misconfiguration disabling the cap entirely.)

## Positive-case guarantee

When validation **passes**, the envelope is never constructed and `execute_tool` proceeds with its normal flow. The validation layer is a pre-check; it does not modify the payload, coerce types, or add default values. This keeps the contract simple: "if validation returns normally, the payload is safe to forward as-is; if validation raises, the envelope replaces the result".

## Testing contract

Per FR-009, the validation layer MUST have parametrized tests covering every tool in `tool.manifest.json`. Minimum test set per tool:

1. **Unknown-key test**: submit `{"__injected__": "value"}` (plus any required properties), assert envelope returned, assert `field == ""`, assert `reason.startswith("unknown property")`.
2. **Type-mismatch test**: for each string parameter, submit an integer value, assert envelope returned, assert `field == "/<param>"`, assert `reason.startswith("expected string")`.
3. **Oversized-string test**: for a string parameter, submit a value of length `DEFAULT_MAX_STRING_LENGTH + 1`, assert envelope returned, assert `reason.startswith("exceeds maxLength")`.

Plus an inventory check that fails the suite when a new tool is added to the manifest without corresponding test coverage (prevents drift).
