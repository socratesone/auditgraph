# Data Model: Pipeline Stages

## Entities

### Stage Contract
- Fields: stage_name, description, required_inputs[], produced_outputs[], manifest_path, entry_criteria, exit_criteria
- Relationships: references manifests produced by upstream stages

### Stage Manifest
- Fields: version, stage, run_id, inputs_hash, outputs_hash, config_hash, status, started_at, finished_at, artifacts[]
- Relationships: links to artifacts and upstream manifests by run_id

### Artifact
- Fields: path, type, hash, size, created_at
- Relationships: referenced by Stage Manifest

### Recovery Rule
- Fields: stage, failure_mode, required_action, cleanup_targets[], rerun_required
- Relationships: tied to Stage Contract

## Validation Rules
- Stage manifest version is required and immutable once written.
- Stage manifest MUST reference only artifacts produced in the same run.
- Manifest is written last after successful atomic artifact writes.
- Inputs hash and outputs hash must be deterministic for identical inputs.

## State Transitions
- Stage run: pending -> running -> completed | failed.
- Failed runs without a manifest are considered incomplete and must be rerun.
