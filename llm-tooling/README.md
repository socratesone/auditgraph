# LLM Tooling

This directory contains the tool manifest and generated artifacts for MCP and LLM adapter integrations.

## Read-Only Mode

Set `READ_ONLY=1` to prevent write or high-risk tools from executing. In this mode, write-classified tools must return `FORBIDDEN` without side effects.

## Error Model

All tools must normalize failures to the following error codes:

- `INVALID_INPUT`
- `NOT_FOUND`
- `CONFLICT`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `TIMEOUT`
- `RATE_LIMITED`
- `UPSTREAM_ERROR`
- `INTERNAL_ERROR`

## Regeneration Steps

1. Update `tool.manifest.json` as the source of truth.
2. Regenerate derived artifacts:
	- `skill.md`
	- `adapters/openai.functions.json`
3. Run contract tests: `pytest -q llm-tooling/tests`
