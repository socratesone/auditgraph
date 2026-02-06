# Feature Specification: Interfaces and UX

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Auditgraph is CLI-first. All commands return JSON with deterministic ordering.

## CLI Commands (day 1)
- `version`
- `init`
- `ingest`
- `import`
- `normalize`
- `extract`
- `link`
- `index`
- `rebuild`
- `query`
- `node`
- `neighbors`
- `diff`
- `export`
- `jobs list`
- `jobs run`
- `why-connected`

## CLI Command Summary

Commands are grouped by workflow:
- Workspace setup: `version`, `init`
- Pipeline stages: `ingest`, `import`, `normalize`, `extract`, `link`, `index`, `rebuild`
- Query and navigation: `query`, `node`, `neighbors`, `why-connected`, `diff`
- Exports and jobs: `export`, `jobs list`, `jobs run`

## Output Requirements
- Commands MUST return JSON to stdout.
- Error cases MUST return `status` fields and message text.
- Deterministic ordering MUST be preserved in lists.

## Editor Integration (Phase 2+)

- Editor integration is deferred beyond day 1.
- Planned actions: open results, insert links.

## Command Output Schemas (minimum)
- Stage commands (`ingest`, `normalize`, `extract`, `link`, `index`, `rebuild`):
  - `stage`, `status`, `detail.manifest`
- `query`: `query`, `results[]`
- `node`: `id`, `type`, `name`, `refs[]`
- `neighbors`: `center_id`, `neighbors[]`
- `diff`: `status`, `added[]`, `removed[]`, `changed[]`
- `export`: `format`, `output`
- `jobs list`: `jobs[]`
- `jobs run`: `status`, `job`, `output`
- `why-connected`: `path[]`

## Acceptance Tests
- Each command returns valid JSON.
- Stage commands return a manifest path on success.
- Error cases are surfaced as structured JSON.

## Success Criteria
- All day-1 CLI commands are implemented and non-placeholder.
