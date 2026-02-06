# Implementation Plan: Pipeline Stages Definition

**Branch**: `005-pipeline-stages` | **Date**: 2026-02-05 | **Spec**: [specs/005-pipeline-stages/spec.md](specs/005-pipeline-stages/spec.md)
**Input**: Feature specification from `/specs/005-pipeline-stages/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define pipeline stage contracts, manifest schemas, and atomicity/recovery rules for ingest, normalize, extract, link, index, and serve. The plan documents inputs, outputs, required manifest fields, dependency validation, and deterministic recovery guidance aligned to the local artifact store.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: None required (stdlib-first)  
**Storage**: Local filesystem, plain-text JSON/JSONL artifacts under `.pkg/`  
**Testing**: pytest  
**Target Platform**: Linux and macOS (MVP)  
**Project Type**: Single-package CLI + spec docs  
**Performance Goals**: p50 < 50ms, p95 < 200ms for keyword search on small datasets  
**Constraints**: Offline-capable, deterministic outputs, stable sorting, auditable artifacts  
**Scale/Scope**: Small/medium datasets (10k-100k docs, up to ~1M entities/claims)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- DRY/SOLID: PASS (documentation-only changes, no new code paths).
- TDD: PASS (no production code changes; future implementation must follow TDD).
- Determinism and simplicity: PASS (spec emphasizes deterministic artifacts and atomic writes).

## Project Structure

### Documentation (this feature)

```text
specs/005-pipeline-stages/
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
├── __init__.py
├── cli.py
├── config.py
├── errors.py
├── export/
├── extract/
├── index/
├── ingest/
├── jobs/
├── link/
├── logging.py
├── normalize/
├── pipeline/
├── plugins/
├── query/
├── scaffold.py
├── storage/
└── utils/

config/
docs/
specs/
tests/
```

**Structure Decision**: Single-package Python CLI with repository-level docs/specs and tests.

## Complexity Tracking

No constitution violations required for this documentation-only feature.

## Phase 0: Outline & Research

**Inputs**: [specs/005-pipeline-stages/spec.md](specs/005-pipeline-stages/spec.md)

**Outputs**: [specs/005-pipeline-stages/research.md](specs/005-pipeline-stages/research.md)

Key research questions resolved:
- Stage contract shape and minimal required fields.
- Manifest schema fields and versioning rules.
- Atomicity, write ordering, and recovery behavior.
- Dependency validation and idempotency expectations.

## Phase 1: Design & Contracts

**Data Model**: [specs/005-pipeline-stages/data-model.md](specs/005-pipeline-stages/data-model.md)

**Contracts**: [specs/005-pipeline-stages/contracts/pipeline-stage-manifests.openapi.yaml](specs/005-pipeline-stages/contracts/pipeline-stage-manifests.openapi.yaml)

**Quickstart**: [specs/005-pipeline-stages/quickstart.md](specs/005-pipeline-stages/quickstart.md)

**Agent Context Update**:
- Run `.specify/scripts/bash/update-agent-context.sh copilot` to sync new tech context.

## Constitution Check (Post-Design)

- DRY/SOLID: PASS
- TDD: PASS (documentation only)
- Determinism: PASS
