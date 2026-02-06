# Quickstart: Pipeline Stage Contracts

## Goal

Use this spec to understand pipeline stage boundaries, manifest schemas, and recovery rules.

## Steps

1. Review [specs/005-pipeline-stages/spec.md](specs/005-pipeline-stages/spec.md) for stage contracts and requirements.
2. Read [specs/005-pipeline-stages/data-model.md](specs/005-pipeline-stages/data-model.md) for manifest and artifact entities.
3. Use [specs/005-pipeline-stages/contracts/pipeline-stage-manifests.openapi.yaml](specs/005-pipeline-stages/contracts/pipeline-stage-manifests.openapi.yaml) to align manifest fields with API consumers.
4. Confirm recovery expectations in the atomicity and recovery section of the spec.

## Success Check

- Each pipeline stage has a documented contract and manifest schema.
- Recovery behavior is explicit for interrupted runs.
