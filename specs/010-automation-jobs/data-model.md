# Data Model: Automation and Jobs

## Entities

### JobConfig
- Fields: name, action.type, action.args, output.path
- Relationships: defines a JobRun

### JobRun
- Fields: job_name, status, output_path, started_at, finished_at
- Relationships: produces JobOutput

### JobOutput
- Fields: path, format
- Relationships: produced by JobRun

## Validation Rules
- Job names are unique.
- `action.type` is required.
- `output.path` defaults to `exports/reports/<job>.md` when missing.
- Missing job definitions return structured errors with non-zero exit codes.

## State Transitions
- JobRun status transitions: `pending` -> `ok` | `failed`.
