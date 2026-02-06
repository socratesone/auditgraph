# Feature Specification: Pipeline Stages

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Auditgraph uses a staged pipeline with deterministic manifests and artifacts for each stage.
Stages are run independently via CLI or combined via `rebuild`.

## Stage Contracts

| Stage | Purpose | Inputs | Outputs | Manifest Path |
| --- | --- | --- | --- | --- |
| ingest | Discover and parse sources into source artifacts. | workspace root, config | source artifacts, ingest manifest | `.pkg/profiles/<profile>/runs/<run_id>/ingest-manifest.json` |
| normalize | Normalize paths/text for downstream use (MVP is no-op). | ingest manifest | normalize manifest | `.pkg/profiles/<profile>/runs/<run_id>/normalize-manifest.json` |
| extract | Build entities/claims from sources. | ingest manifest, source artifacts | entity/claim artifacts, extract manifest | `.pkg/profiles/<profile>/runs/<run_id>/extract-manifest.json` |
| link | Generate deterministic links and adjacency index. | extract manifest, entities/claims | link artifacts, adjacency index, link manifest | `.pkg/profiles/<profile>/runs/<run_id>/link-manifest.json` |
| index | Build search indexes. | link manifest, entities/links | index artifacts, index manifest | `.pkg/profiles/<profile>/runs/<run_id>/index-manifest.json` |

## Manifest Schema (all stages)
Each stage manifest MUST include:

- `version`, `stage`, `run_id`
- `inputs_hash`, `outputs_hash`, `config_hash`
- `status`, `started_at`, `finished_at`
- `artifacts` (list of produced artifact paths)

## Atomicity and Recovery
- Artifacts are written to final paths deterministically; manifests are written last.
- If a manifest is missing, the stage MUST be rerun.

## CLI Triggers
- `auditgraph ingest`
- `auditgraph normalize`
- `auditgraph extract`
- `auditgraph link`
- `auditgraph index`
- `auditgraph rebuild`

## Acceptance Tests
- Ingest manifest path is under `runs/<run_id>/`.
- Extract, link, and index manifests are written with required fields.
- Running `rebuild` produces the same `run_id` for identical inputs.

## Success Criteria
- 100% of stages produce manifests with required fields.
- Stage outputs are deterministic for identical inputs and config.
