# Implementation Plan: Linking and Explainability

**Branch**: `007-linking-explainability` | **Date**: 2026-02-05 | **Spec**: [specs/007-linking-explainability/spec.md](specs/007-linking-explainability/spec.md)
**Input**: Feature specification from `/specs/007-linking-explainability/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define deterministic link rules, explainability payloads, and backlinks policy. The plan documents link generation policy, required metadata, explainability fields, and deterministic ordering to keep links auditable and reproducible.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: None required (stdlib-first)  
**Storage**: Local filesystem, plain-text JSON/JSONL artifacts under `.pkg/`  
**Testing**: pytest  
**Target Platform**: Linux and macOS (MVP)  
**Project Type**: Single-package CLI + spec docs  
**Performance Goals**: <1s for graph traversal and why-connected queries  
**Constraints**: Offline-capable, deterministic outputs, stable sorting, explainable artifacts  
**Scale/Scope**: Small/medium datasets (10k-100k docs, up to ~1M entities/claims)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- DRY/SOLID: PASS (documentation-only changes, no new code paths).
- TDD: PASS (no production code changes; future implementation must follow TDD).
- Determinism and simplicity: PASS (spec emphasizes deterministic linking).

## Project Structure

### Documentation (this feature)

```text
specs/007-linking-explainability/
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

**Inputs**: [specs/007-linking-explainability/spec.md](specs/007-linking-explainability/spec.md)

**Outputs**: [specs/007-linking-explainability/research.md](specs/007-linking-explainability/research.md)

Key research questions resolved:
- Link generation policy and authoritative vs suggested behavior.
- Required link metadata and explainability payload fields.
- Backlinks policy and deterministic ordering rules.

## Phase 1: Design & Contracts

**Data Model**: [specs/007-linking-explainability/data-model.md](specs/007-linking-explainability/data-model.md)

**Contracts**: [specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml](specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml)

**Quickstart**: [specs/007-linking-explainability/quickstart.md](specs/007-linking-explainability/quickstart.md)

**Agent Context Update**:
- Run `.specify/scripts/bash/update-agent-context.sh copilot` to sync new tech context.

## Constitution Check (Post-Design)

- DRY/SOLID: PASS
- TDD: PASS (documentation only)
- Determinism: PASS
