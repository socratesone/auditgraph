# Research: Pipeline Stages Definition

## Decision 1: Stage Contract Shape

- **Decision**: Define a stage contract with stage name, required inputs, produced outputs, entry/exit criteria, and manifest location.
- **Rationale**: This is the minimal shape that supports coordination between stages and ensures deterministic handoffs.
- **Alternatives considered**: Separate contracts for inputs vs outputs; single pipeline table only. Rejected because per-stage ownership becomes unclear.

## Decision 2: Manifest Schema Fields

- **Decision**: Require manifest fields: stage, run_id, inputs_hash, outputs_hash, config_hash, status, started_at, finished_at, artifacts, and version.
- **Rationale**: These fields capture determinism, auditability, and tie each manifest to a specific run and configuration.
- **Alternatives considered**: Minimal fields (stage/run_id only). Rejected because it undermines audit and diff workflows.

## Decision 3: Atomicity Strategy

- **Decision**: Write artifacts to temp paths, then atomically rename/move into place; write the manifest last.
- **Rationale**: Writing the manifest last provides a clear completion signal and supports safe recovery.
- **Alternatives considered**: Write manifest first, or rely on partial writes with no atomicity. Rejected due to ambiguous completion signals.

## Decision 4: Recovery Behavior

- **Decision**: If a manifest exists, treat artifacts as complete; if a manifest is missing, rebuild the stage outputs. Discard partial temp files.
- **Rationale**: This provides a deterministic recovery rule and avoids trusting partial outputs.
- **Alternatives considered**: Reuse artifacts without a manifest. Rejected due to higher risk of inconsistent outputs.

## Decision 5: Dependency Validation

- **Decision**: Require upstream manifests for the same run_id before stage execution.
- **Rationale**: Ensures explicit failure modes when inputs are missing and supports idempotent reruns.
- **Alternatives considered**: Hash-only compatibility checks or best-effort runs. Rejected due to ambiguity in run lineage.
