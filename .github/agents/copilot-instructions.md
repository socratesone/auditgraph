# auditgraph Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-05

## Active Technologies
- Local filesystem (plain-text JSON/JSONL artifacts) (001-spec-plan)
- Python 3.10+ + None required for MVP (stdlib-first); optional: PyYAML for config (002-data-sources-ingestion)
- Local filesystem (plain-text artifacts) (002-data-sources-ingestion)
- Local filesystem (plain-text artifacts and manifests) (003-determinism-audit-contract)
- Python 3.10+ + None required (stdlib-first) (005-pipeline-stages)
- Local filesystem, plain-text JSON/JSONL artifacts under `.pkg/` (005-pipeline-stages)
- Python 3.10+ + PyYAML (config parsing), stdlib (010-automation-jobs)
- Local filesystem under workspace root and `.pkg/` (010-automation-jobs)
- Python >=3.10 + stdlib, `pyyaml` (config), `pytest` (tests) (011-security-privacy-compliance)
- Filesystem artifacts under `.pkg/profiles/<profile>/...` and `exports/...` (011-security-privacy-compliance)
- Python >=3.10 + stdlib, PyYAML (config), pytest (tests) (012-distribution-packaging-upgrades)
- Filesystem artifacts under per-profile `.pkg` directories (012-distribution-packaging-upgrades)
- Python >=3.10 + stdlib, pytest (013-testing-quality-gates)
- Filesystem artifacts under `.pkg` (fixtures and golden artifacts) (013-testing-quality-gates)

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
- 013-testing-quality-gates: Added Python >=3.10 + stdlib, pytest
- 012-distribution-packaging-upgrades: Added Python >=3.10 + stdlib, PyYAML (config), pytest (tests)
- 011-security-privacy-compliance: Added Python >=3.10 + stdlib, `pyyaml` (config), `pytest` (tests)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
