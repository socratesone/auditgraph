# Data Model: Interfaces and UX

## Entities

### Command
- Fields: name, description, inputs, outputs, exit_codes
- Relationships: emits OutputPayload

### OutputPayload
- Fields: status, data, errors, warnings
- Relationships: produced by Command

### InterfacePolicy
- Fields: cli_first, web_ui_optional, editor_integration_depth
- Relationships: applies to command behavior

### IntegrationSurface
- Fields: actions, phase
- Relationships: defines editor features

## Validation Rules
- JSON outputs include status and data fields.
- Errors are reported with non-zero exit codes and structured payloads in JSON mode.

## State Transitions
- Command outputs are immutable once returned.
