# Implementation Plan: Automation and Jobs

**Branch**: `010-automation-jobs` | **Date**: 2026-02-06 | **Spec**: [specs/010-automation-jobs/spec.md](specs/010-automation-jobs/spec.md)
**Input**: Feature specification from `/specs/010-automation-jobs/spec.md`

**Note**: This plan follows the `/speckit.plan` workflow.

## Summary

Define manual job execution, a validated job configuration schema, and deterministic output storage for automation jobs, with structured error handling and clear CLI responses.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: PyYAML (config parsing), stdlib  
**Storage**: Local filesystem under workspace root and `.pkg/`  
**Testing**: pytest  
**Target Platform**: Linux and macOS (MVP)  
**Project Type**: Single-package CLI  
**Performance Goals**: Job execution and listing < 1s for metadata operations  
**Constraints**: Offline-capable, deterministic outputs, stable sorting  
**Scale/Scope**: Dozens of jobs, outputs stored in workspace

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- DRY/SOLID: PASS (shared job config parsing and runner modules).
- TDD: PASS (tests required for config parsing and job execution behavior).
- Determinism: PASS (sorted job listings and fixed output paths).

## Project Structure

### Documentation (this feature)

```text
specs/010-automation-jobs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
auditgraph/
├── cli.py
├── jobs/
│   ├── config.py
│   ├── reports.py
│   └── runner.py
└── storage/

config/
docs/
specs/
tests/
```

**Structure Decision**: Single-package Python CLI with dedicated `auditgraph/jobs` modules for job config, execution, and reporting.

## Complexity Tracking

No constitution violations required.

## Phase 0: Outline & Research

**Inputs**: [specs/010-automation-jobs/spec.md](specs/010-automation-jobs/spec.md)

**Outputs**: [specs/010-automation-jobs/research.md](specs/010-automation-jobs/research.md)

Key research questions resolved:
- Scheduler scope (manual only for MVP).
- Jobs config location and schema.
- Supported actions and output storage rules.
- Structured error reporting requirements.

## Phase 1: Design & Contracts

**Data Model**: [specs/010-automation-jobs/data-model.md](specs/010-automation-jobs/data-model.md)

**Contracts**: [specs/010-automation-jobs/contracts/automation-jobs.openapi.yaml](specs/010-automation-jobs/contracts/automation-jobs.openapi.yaml)

**Quickstart**: [specs/010-automation-jobs/quickstart.md](specs/010-automation-jobs/quickstart.md)

**Agent Context Update**:
- Run `.specify/scripts/bash/update-agent-context.sh copilot` to sync new tech context.

## Constitution Check (Post-Design)

- DRY/SOLID: PASS
- TDD: PASS
- Determinism: PASS
