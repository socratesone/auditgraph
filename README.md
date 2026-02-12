![auditgraph](docs/img/auditgraph-hero.png)

# auditgraph

Local-first, deterministic personal knowledge graph tooling for engineers.

[![License](https://img.shields.io/badge/license-SEE%20LICENSE-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-enabled-brightgreen)](MCP_GUIDE.md)

Auditgraph ingests plain-text notes and code, deterministically extracts entities and claims, builds explainable links, and provides CLI-first navigation. Your source of truth stays in plain text; derived artifacts are reproducible, diffable, and fully audited.

## Overview

Auditgraph solves the "where did this fact come from?" problem for technical notes and code. It turns local content into a deterministic knowledge graph with stable IDs, audit logs, and reproducible outputs so you can trace and verify every derived artifact.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [MCP (LLM Tooling)](#mcp-llm-tooling)
- [Contributing](#contributing)
- [Tests](#tests)
- [License](#license)
- [Contact](#contact)

## Features

- Local-first, offline-capable PKG for engineers and teams.
- Deterministic ingestion, extraction, linking, indexing, and query with stable IDs.
- Audit trail for runs, manifests, and provenance.
- CLI-first workflows with optional local UI planned.
- Optional LLM-assisted extraction as a replayable, fully logged step.

## Installation

```bash
pip install auditgraph
auditgraph version
```

Development install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Shortcut: `make dev` (creates `.venv` and installs requirements).

## Usage

Initialize a workspace:

```bash
auditgraph init --root .
```

Run ingestion and query:

```bash
auditgraph ingest --root . --config config/pkg.yaml
auditgraph query --q "symbol" --root . --config config/pkg.yaml
```

Inspect nodes and neighbors:

```bash
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
```

Diff runs and export:

```bash
auditgraph diff --run-a <run_id> --run-b <run_id> --root . --config config/pkg.yaml
auditgraph export --format json --root . --config config/pkg.yaml
```

Jobs:

```bash
auditgraph jobs list --root .
auditgraph jobs run changed_since --root . --config config/pkg.yaml
```

## Configuration

- Jobs configuration: `config/jobs.yaml`
- Package configuration: `config/pkg.yaml`
- Redaction key: `.pkg/profiles/<profile>/secrets/redaction.key`

See [docs/environment-setup.md](docs/environment-setup.md) for environment details.

## CLI Reference

```bash
auditgraph version
auditgraph init --root .
auditgraph ingest --root . --config config/pkg.yaml
auditgraph import docs/notes.md logs/ --root . --config config/pkg.yaml
auditgraph normalize --root . --config config/pkg.yaml
auditgraph extract --root . --config config/pkg.yaml
auditgraph link --root . --config config/pkg.yaml
auditgraph index --root . --config config/pkg.yaml
auditgraph query --q "symbol" --root . --config config/pkg.yaml
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
auditgraph diff --run-a <run_id> --run-b <run_id> --root . --config config/pkg.yaml
auditgraph export --format json --root . --config config/pkg.yaml
auditgraph jobs list --root .
auditgraph jobs run <job_name> --root . --config config/pkg.yaml
```

## MCP (LLM Tooling)

The MCP/LLM integration artifacts live under `llm-tooling/`:

- `llm-tooling/tool.manifest.json` is the source of truth.
- `llm-tooling/skill.md` and `llm-tooling/adapters/openai.functions.json` are generated outputs.

Regenerate artifacts after manifest updates:

```bash
python llm-tooling/generate_skill_doc.py
python llm-tooling/generate_adapters.py
```

MCP server utilities live in `llm-tooling/mcp/server.py`. Set `READ_ONLY=1` to block write or high-risk tools.

For VS Code MCP setup, see [MCP_GUIDE.md](MCP_GUIDE.md).

## Contributing

1. Fork the repo and create a feature branch.
2. Create a virtual environment and install dev dependencies.
3. Run tests before opening a PR.

Dev setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Project assumptions and decisions live in [docs/clarifying-answers.md](docs/clarifying-answers.md) and [SPEC.md](SPEC.md).

## Tests

```bash
make test
```

Or:

```bash
pytest
```

## License

See [LICENSE](LICENSE).

## Contact

Open an issue in the repository for questions, bug reports, or feature requests.
