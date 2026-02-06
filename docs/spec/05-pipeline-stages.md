# Pipeline & Stages

## Purpose
Define stage boundaries, inputs/outputs, manifests, and atomicity rules.

## Source material
- [SPEC.md](SPEC.md) Architecture, Pipeline stages

## Decisions Required
- Stage contracts for ingest/normalize/extract/link/index/serve.
- Manifest schema for each stage (required fields, versioning).
- Atomic write/move strategy and recovery behavior.

## Decisions (filled)

### Stage Contracts

All stages follow the same contract shape: purpose, required inputs, produced outputs, entry criteria, exit criteria, and manifest path.

| Stage | Purpose | Required Inputs | Produced Outputs | Entry Criteria | Exit Criteria | Manifest Path |
| --- | --- | --- | --- | --- | --- | --- |
| ingest | Discover and parse source files into source records. | Workspace root, config, include/exclude rules. | Source artifacts and ingest manifest. | Root exists; config loaded. | Ingest manifest written. | `.pkg/profiles/<profile>/runs/<run_id>/ingest-manifest.json` |
| normalize | Apply canonical text and path normalization. | Ingest manifest, raw source artifacts. | Normalized source artifacts. | Ingest manifest exists for run. | Normalized artifacts written. | `.pkg/profiles/<profile>/runs/<run_id>/normalize-manifest.json` |
| extract | Produce entities/claims from normalized sources. | Normalized artifacts, extraction rules. | Entity/claim artifacts, extract manifest. | Normalized artifacts exist. | Extract manifest written. | `.pkg/profiles/<profile>/runs/<run_id>/extract-manifest.json` |
| link | Build deterministic links between entities/claims. | Entity/claim artifacts, link rules. | Link artifacts, adjacency index, link manifest. | Extract manifest exists. | Link manifest written. | `.pkg/profiles/<profile>/runs/<run_id>/link-manifest.json` |
| index | Build search indexes and graph indexes. | Entity/claim/link artifacts. | Index artifacts, index manifest. | Link manifest exists. | Index manifest written. | `.pkg/profiles/<profile>/runs/<run_id>/index-manifest.json` |
| serve | Provide query/CLI output and exports. | Index artifacts, manifests. | Query responses, export artifacts. | Index manifest exists. | Export/report written (if requested). | `.pkg/profiles/<profile>/runs/<run_id>/serve-manifest.json` |

### Manifest Schemas

Each stage writes a manifest with required fields and a version identifier.

Required fields:
- `version`
- `stage`
- `run_id`
- `inputs_hash`
- `outputs_hash`
- `config_hash`
- `status`
- `started_at`
- `finished_at`
- `artifacts` (list of artifact paths and metadata)

Versioning rules:
- `version` is required and immutable once written.
- Manifest schema changes must bump the `version` value.

### Atomicity and Recovery

- Write artifacts to temp paths.
- Atomically rename/move artifacts into place.
- Write the manifest last as the completion signal.
- If the manifest is missing, discard temp artifacts and rebuild.
- Dependency validation requires upstream manifests for the same `run_id`.

## Resolved

- Stage contracts and manifest schemas documented for ingest, normalize, extract, link, index, serve.
- Atomic write strategy uses temp paths and manifest-last completion.
- Recovery behavior: no manifest means rerun; manifests imply complete artifacts.
