# Feature Specification: Determinism and Audit Contract

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Auditgraph guarantees deterministic outputs and auditable provenance for all stages.
Run identifiers, manifests, and ordering rules must be stable for identical inputs and config.

## Requirements

### Functional Requirements
- **FR-001**: Run identifiers MUST be derived from `inputs_hash` and `config_hash`.
- **FR-002**: Every stage MUST write a manifest with `run_id`, `stage`, `inputs_hash`, `outputs_hash`, `config_hash`.
- **FR-003**: A config snapshot MUST be written per run to `runs/<run_id>/config-snapshot.json`.
- **FR-004**: A replay log entry MUST be written per stage to `runs/<run_id>/replay-log.jsonl`.
- **FR-005**: Provenance records MUST be written for every derived artifact.
- **FR-006**: Failures MUST be recorded as skipped with explicit reasons; no silent drops.
- **FR-007**: Query ordering MUST be deterministic for equal scores using explicit tie-break keys.

### Non-Functional Requirements
- **NFR-001**: Deterministic outputs MUST be byte-for-byte identical for identical inputs and config.

## Manifest Schema (all stages)
Each stage manifest MUST include:

- `version`, `stage`, `run_id`
- `inputs_hash`, `outputs_hash`, `config_hash`
- `status`, `started_at`, `finished_at`
- `artifacts` (paths of produced artifacts)

## Determinism Rules
- File discovery order is sorted by normalized path.
- Hash inputs are sorted before hashing.
- `started_at` and `finished_at` are deterministic placeholders for reproducibility.

## Audit Artifacts
- `runs/<run_id>/config-snapshot.json`
- `runs/<run_id>/replay-log.jsonl`
- `provenance/<run_id>.json`

## Acceptance Tests
- Deterministic run id for identical inputs and config.
- Provenance index exists and contains records.
- Replay log contains a stage entry.
- Stable tie-break ordering for equal scores.

## Success Criteria
- 100% of repeated runs with identical inputs produce identical manifests.
- 100% of derived artifacts have provenance records.
