# Implementation Plan: Storage Layout and Artifacts

**Branch**: `006-storage-layout-artifacts` | **Date**: 2026-02-05 | **Spec**: [specs/006-storage-layout-artifacts/spec.md](specs/006-storage-layout-artifacts/spec.md)
**Input**: Feature specification from `/specs/006-storage-layout-artifacts/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define canonical storage layout, artifact schemas, sharding rules, and stable ID canonicalization for sources, entities, claims, links, and indexes under `.pkg/profiles/<profile>/`. This plan documents the required directories, artifact fields, and versioning rules to keep outputs deterministic and auditable.

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
- Determinism and simplicity: PASS (spec emphasizes deterministic IDs and stable layout).

## Project Structure

### Documentation (this feature)

```text
specs/006-storage-layout-artifacts/
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

**Inputs**: [specs/006-storage-layout-artifacts/spec.md](specs/006-storage-layout-artifacts/spec.md)

**Outputs**: [specs/006-storage-layout-artifacts/research.md](specs/006-storage-layout-artifacts/research.md)

Key research questions resolved:
- Canonical directory layout and naming conventions for artifacts.
- Required fields and versioning rules for each artifact schema.
- Sharding rules and ID prefix strategy.
- Stable ID canonicalization inputs and hashing rules.

## Phase 1: Design & Contracts

**Data Model**: [specs/006-storage-layout-artifacts/data-model.md](specs/006-storage-layout-artifacts/data-model.md)

**Contracts**: [specs/006-storage-layout-artifacts/contracts/storage-artifacts.openapi.yaml](specs/006-storage-layout-artifacts/contracts/storage-artifacts.openapi.yaml)

**Quickstart**: [specs/006-storage-layout-artifacts/quickstart.md](specs/006-storage-layout-artifacts/quickstart.md)

**Agent Context Update**:
- Run `.specify/scripts/bash/update-agent-context.sh copilot` to sync new tech context.

## Constitution Check (Post-Design)

- DRY/SOLID: PASS
- TDD: PASS (documentation only)
- Determinism: PASS
