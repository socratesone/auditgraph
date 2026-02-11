# Implementation Plan: Distribution, Packaging, and Upgrades

**Branch**: `012-distribution-packaging-upgrades` | **Date**: 2026-02-11 | **Spec**: [specs/012-distribution-packaging-upgrades/spec.md](spec.md)
**Input**: Feature specification from `/specs/012-distribution-packaging-upgrades/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define and implement distribution rules for Linux/macOS packaging, enforce artifact schema compatibility on upgrade, and apply disk footprint budgets that warn at 80% and block at 100% of the configured limit.

## Technical Context

**Language/Version**: Python >=3.10  
**Primary Dependencies**: stdlib, PyYAML (config), pytest (tests)  
**Storage**: Filesystem artifacts under per-profile `.pkg` directories  
**Testing**: pytest (unit + integration)  
**Target Platform**: Linux (x86_64), macOS (Intel/Apple Silicon)  
**Project Type**: Single Python package (`auditgraph/`)  
**Performance Goals**: Budget checks complete in under 50ms per run on typical workspaces  
**Constraints**: Offline-capable, deterministic outputs, no Windows support for day 1  
**Scale/Scope**: Local workspaces (10s-1000s files per run)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **DRY**: Centralize schema compatibility and budget enforcement logic in shared utilities.
- **SOLID**: Separate policy evaluation (compatibility, budget) from CLI and pipeline orchestration.
- **TDD (non-negotiable)**: Add failing tests for compatibility checks and budget thresholds before implementation.
- **Determinism**: Compatibility decisions and budget calculations must be deterministic.

GATE STATUS: PASS

## Project Structure

### Documentation (this feature)

```text
specs/012-distribution-packaging-upgrades/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
auditgraph/
├── cli.py
├── config.py
├── pipeline/
├── storage/
├── utils/
└── ingest/

config/
├── pkg.yaml
└── jobs.yaml

tests/
├── test_cli_integration.py
├── test_smoke.py
└── test_spec012_*.py  # to be added for this feature
```

**Structure Decision**: Single Python package with pytest tests under `tests/`.

## Phase 0 Research

- Outputs in [specs/012-distribution-packaging-upgrades/research.md](research.md).

## Phase 1 Design

- Data model: [specs/012-distribution-packaging-upgrades/data-model.md](data-model.md).
- Contracts: [specs/012-distribution-packaging-upgrades/contracts/distribution.openapi.yaml](contracts/distribution.openapi.yaml).
- Quickstart: [specs/012-distribution-packaging-upgrades/quickstart.md](quickstart.md).

## Constitution Check (Post-Design)

- DRY/SOLID/TDD/Determinism remain satisfied with centralized policy utilities and deterministic budget calculations.

GATE STATUS: PASS

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
