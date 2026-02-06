# Research: Automation and Jobs

## Decision 1: Scheduler Scope

- **Decision**: Manual execution only for MVP (no scheduler).
- **Rationale**: Delivers value without background daemons or OS-specific schedulers.
- **Alternatives considered**: Cron-like scheduling in config. Rejected due to scope.

## Decision 2: Configuration Schema Location

- **Decision**: Jobs are configured in `config/jobs.yaml`.
- **Rationale**: Matches existing config conventions and keeps jobs explicit.
- **Alternatives considered**: Inline config in `pkg.yaml`. Rejected to avoid coupling.

## Decision 3: Supported Actions

- **Decision**: Support `report.changed_since` as the initial action type.
- **Rationale**: Existing report utility aligns with current code and deterministic output.
- **Alternatives considered**: Free-form commands. Rejected to preserve determinism.

## Decision 4: Output Storage

- **Decision**: Outputs are written to `exports/reports/<job>.md` by default, overridable by `output.path`.
- **Rationale**: Predictable location for reports with explicit overrides.
- **Alternatives considered**: Per-run output directories. Deferred for now.

## Decision 5: Error Reporting

- **Decision**: Missing or invalid jobs return structured errors and non-zero exit codes.
- **Rationale**: Enables automation and predictable CLI behavior.
- **Alternatives considered**: Silent skips. Rejected due to poor UX.
