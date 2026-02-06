# auditgraph Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-05

## Active Technologies
- Local filesystem (plain-text JSON/JSONL artifacts) (001-spec-plan)
- Python 3.10+ + None required for MVP (stdlib-first); optional: PyYAML for config (002-data-sources-ingestion)
- Local filesystem (plain-text artifacts) (002-data-sources-ingestion)
- Local filesystem (plain-text artifacts and manifests) (003-determinism-audit-contract)
- Python 3.10+ + None required (stdlib-first) (005-pipeline-stages)
- Local filesystem, plain-text JSON/JSONL artifacts under `.pkg/` (005-pipeline-stages)

- Python 3.10+ + None required for MVP (stdlib-first); optional: rich (CLI UX), fastapi (optional local UI API) (001-spec-plan)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+: Follow standard conventions

## Recent Changes
- 005-pipeline-stages: Added Python 3.10+ + None required (stdlib-first)
- 005-pipeline-stages: Added Python 3.10+ + None required (stdlib-first)
- 004-knowledge-model: Added Python 3.10+ + None required for MVP (stdlib-first)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
