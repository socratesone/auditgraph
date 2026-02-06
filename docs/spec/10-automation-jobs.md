# Automation & Jobs

## Purpose
Define scheduler model, job definitions, outputs, and review queue lifecycle.

## Source material
- [SPEC.md](SPEC.md) Automation Framework
- [SPEC.md](SPEC.md) Functional Requirements FR-7

## Decisions Required
- Job scheduler model and trigger support.
- jobs.yaml schema and validation rules.
- Output storage paths and artifact conventions.
- Review queue lifecycle and decision storage.

## Decisions (filled)

### Scheduler Model

- Scheduled jobs defined in config
- Manual trigger via CLI

### jobs.yaml Schema

- `jobs` map with name
- `schedule` (cron-like string or "manual")
- `action` with `type` and `args`
- `output` with `path`

### Output Conventions

- Job outputs stored under `exports/reports/` by default
- Outputs are plain-text artifacts

### Review Queue Lifecycle

- Proposed links/claims stored as plain-text queue entries
- Accept/reject decisions recorded as plain-text updates

## Resolved

- Scheduler model and jobs.yaml schema defined
- Output conventions defined
- Review queue lifecycle defined

## Resolved
- None yet.
