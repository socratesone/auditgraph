# Interfaces and UX

## Purpose
Define the CLI command surface, output schemas, and error handling for day-1 usage.

## Command Surface (Day 1)

All commands output JSON to stdout. Commands accept `--root` and `--config` where applicable.

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

## Output Schemas (Minimum)

Stage commands (`ingest`, `normalize`, `extract`, `link`, `index`, `rebuild`):
- `stage`, `status`, `detail.manifest`

`version`:
- `version`

`query`:
- `query`, `results[]`

`node`:
- `id`, `type`, `name`, `refs[]`

`neighbors`:
- `center_id`, `neighbors[]`

`diff`:
- `status`, `added[]`, `removed[]`, `changed[]`

`export`:
- `format`, `output`

`jobs list`:
- `jobs[]`

`jobs run`:
- `status`, `job`, `output`

`why-connected`:
- `path[]`

## Error Handling

- Errors MUST return JSON with `status` and `message` fields.
- Error responses MUST return non-zero exit codes.

## Determinism

- Output ordering MUST be deterministic for lists.
- Stable sorting is required for repeated queries and exports.

## Editor Integration

- Deferred to phase 2+.
- Planned actions: open results, insert links.

## Acceptance Checks

- Each command returns valid JSON.
- Stage commands return a manifest path on success.
- Errors return structured payloads with `status` and `message`.
