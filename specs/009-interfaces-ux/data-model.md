# Data Model: Interfaces and UX

## Entities

### Command
- Fields: name, description, inputs, outputs, exit_codes
- Relationships: emits OutputPayload

### OutputPayload
- Fields: status, message, detail
- Relationships: produced by Command

### InterfacePolicy
- Fields: cli_first, web_ui_optional, editor_integration_depth
- Relationships: applies to command behavior

### IntegrationSurface
- Fields: actions, phase
- Relationships: defines editor features

## Validation Rules
- All command outputs are JSON objects.
- Error payloads include `status` and `message`.
- Success payloads follow per-command minimum fields from spec.md.
- Errors return non-zero exit codes.
- Editor integration `phase` must be `phase2+` or later.

## State Transitions
- Command outputs are immutable once returned.
