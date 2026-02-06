# Data Model

## Entities

### RunManifest
- Fields: run_id, pipeline_version, config_hash, inputs_hash, outputs_hash, started_at, stages[]

### ProvenanceRecord
- Fields: artifact_id, source_path, source_hash, rule_id, input_hash, run_id

### ConfigSnapshot
- Fields: config_hash, stored_path, run_id

## Validation Rules
- Every derived artifact must reference a provenance record.
- Every run must store manifest and replay log.
- Config snapshot hash must match stored snapshot.

## State Transitions
- Run initiated → manifest created → replay log appended → outputs recorded
