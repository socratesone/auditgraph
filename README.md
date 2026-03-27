![auditgraph](docs/img/auditgraph-hero.png)

# auditgraph

Local-first, deterministic personal knowledge graph tooling for engineers.

[![License](https://img.shields.io/badge/license-SEE%20LICENSE-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-enabled-brightgreen)](MCP_GUIDE.md)

Auditgraph ingests plain-text notes, code, and day-1 `.pdf`/`.docx` documents, deterministically extracts entities and claims, builds explainable links, and provides CLI-first navigation. Your source of truth stays in plain text; derived artifacts are reproducible, diffable, and fully audited.

Status: early-stage CLI project (`v0.1.0`) focused on local developer workflows.

Primary audience: developers/engineers who want deterministic, inspectable knowledge graph artifacts from local content.

## Overview

Auditgraph solves the "where did this fact come from?" problem for technical notes and code. It turns local content into a deterministic knowledge graph with stable IDs, audit logs, and reproducible outputs so you can trace and verify every derived artifact.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Behavior Notes](#behavior-notes)
- [Troubleshooting](#troubleshooting)
- [Neo4j Export and Sync](#neo4j-export-and-sync)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Developer Docs](#developer-docs)
- [Tests](#tests)
- [License](#license)
- [Contact](#contact)

## Features

- Local-first, offline-capable PKG for engineers and teams.
- Deterministic ingestion, extraction, linking, indexing, and query with stable IDs.
- Day-1 document ingestion for `.pdf` and `.docx` with deterministic chunking and metadata-only citations.
- Keyword index for entity names and aliases, with case-insensitive exact-key lookup.
- Audit trail for runs, manifests, and provenance.
- CLI-first workflows with optional local UI planned.
- Neo4j export/sync support with stable ordering and direct database sync (export headers include run timestamp metadata).
- Full pipeline replay from stored config snapshots.
- Run diff for comparing ingest manifests across runs.
- Subgraph export in JSON, DOT, and GraphML formats.

### Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| File ingestion (text, markdown, code) | Implemented | Deterministic with stable IDs |
| PDF/DOCX ingestion | Implemented | OCR mode: off/auto/on |
| Entity extraction | Implemented | Notes, code symbols |
| NER entity extraction | Implemented | Requires `spacy`; enable via config |
| Linking (co-occurrence) | Implemented | Explainable links with provenance |
| BM25 keyword index | Implemented | Case-insensitive exact-key lookup |
| Query and search | Implemented | Entity + chunk matching |
| Run diff | Implemented | Structural diff of ingest manifests |
| Subgraph export (JSON/DOT/GraphML) | Implemented | With budget checks and path safety |
| Neo4j export/sync | Implemented | Cypher export + live database sync |
| Jobs automation | Implemented | YAML-configured job runner |
| Pipeline replay | Implemented | Re-run from stored config snapshots |
| Schema versioning | Implemented | `v1` with compatibility checks |
| Markdown sub-entities | Planned | Code exists but not wired into pipeline |
| Semantic/vector search | Planned | Index stub only; no embeddings yet |
| LLM-assisted extraction | Planned | Config key exists; no implementation |
| Local UI | Planned | CLI-only for now |

## Installation

Prerequisites:

- Python 3.10+
- Linux (x86_64) or macOS (Intel/Apple Silicon) for day-1 support
- `git`

Auditgraph is not published to PyPI yet. Install from source:

```bash
git clone https://github.com/socratesone/auditgraph
cd auditgraph
python -m venv .venv
source .venv/bin/activate
pip install -e .
auditgraph version
```

Shortcut: `make dev` (creates `.venv` and installs requirements).

## Quick Start

Initialize a workspace and run the full pipeline:

```bash
auditgraph init --root .
auditgraph run examples/sample_docs/
```

Or run individual stages:

```bash
auditgraph ingest --root . --config config/pkg.yaml
auditgraph query --q "symbol" --root . --config config/pkg.yaml
```

One-command setup for development:

```bash
make setup
```

For first-success output examples and a fuller walkthrough, see [QUICKSTART.md](QUICKSTART.md).

## Behavior Notes

### Query behavior

Entity matching is currently case-insensitive exact-key lookup against the BM25 index entries (names and aliases). Query text is not expanded into per-token search terms at query time.

Chunk matching is case-insensitive substring matching over chunk text.

For example, querying `"auth_token"` matches entities indexed as `auth_token` and chunks containing `auth_token` text. It does not currently fan out to independent `auth` and `token` lookups.

### Content extraction

Current extract stage behavior:

- Creates note entities from markdown files.
- Extracts code symbols from supported source files.
- Extracts NER entities from chunks when `profiles.<name>.extraction.ner.enabled: true`.

Planned markdown sub-entities (implemented in extractor code but not wired into the default extract pipeline yet):

- **`ag:section`** — one entity per heading (`# Heading` through `###### Heading`), with the heading level and source line recorded.
- **`ag:technology`** — one entity per recognized technology mention (languages, frameworks, databases, tools). Over 80 technologies are recognized including Python, Neo4j, FastAPI, React, Docker, etc.
- **`ag:reference`** — one entity per markdown link (`[text](url)`), with the URL stored in aliases and metadata.

Note: these planned markdown sub-entities are not produced by default in the current pipeline.

Document ingestion defaults:

- OCR mode defaults to `off` (supported values: `off|auto|on`).
- `.doc` is rejected in day-1 scope with explicit machine-readable reasons.
- Chunk citations are returned as metadata fields (`source_path`, page/paragraph location), not inline markers.

## Troubleshooting

- If you see `Missing schema_version in manifest`, run:

	```bash
	auditgraph rebuild --root . --config config/pkg.yaml
	```

- If `auditgraph` command is not found, re-activate your venv:

	```bash
	source .venv/bin/activate
	```

- If config loading fails due to missing YAML support, install dev dependencies:

	```bash
	make dev
	```

## Neo4j Export and Sync

Auditgraph supports exporting graph artifacts to Neo4j-compatible Cypher and syncing directly to a running Neo4j instance.

Set Neo4j connection variables:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"      # or NEO4J_USERNAME
export NEO4J_PASSWORD="<your_password>"
export NEO4J_DATABASE="neo4j"
```

Export to a `.cypher` artifact:

```bash
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/graph.cypher
```

Dry-run sync (no DB mutation):

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
```

Live sync:

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

For full setup and validation workflow, see [specs/001-neo4j-export-sync/quickstart.md](specs/001-neo4j-export-sync/quickstart.md).

## Configuration

- Jobs configuration: `config/jobs.yaml`
- Package configuration: `config/pkg.yaml`
- Redaction key: `.pkg/profiles/<profile>/secrets/redaction.key`

See [docs/environment-setup.md](docs/environment-setup.md) for environment details.

## CLI Reference

```bash
auditgraph --help
auditgraph version
auditgraph init --root .
auditgraph run examples/sample_docs/               # Full pipeline
auditgraph ingest --root . --config config/pkg.yaml
auditgraph rebuild --root . --config config/pkg.yaml
auditgraph query --q "symbol" --root . --config config/pkg.yaml
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
auditgraph diff --run-a <run_id_1> --run-b <run_id_2> --root .
auditgraph export --format json --root . --config config/pkg.yaml
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/graph.cypher
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
auditgraph replay <run_id> --root .                 # Replay a previous run
auditgraph jobs list --root .
```

For the full command surface, run `auditgraph --help`.

## Developer Docs

Documentation map:

- First-success walkthrough with expected output: [QUICKSTART.md](QUICKSTART.md)
- Environment and platform details: [docs/environment-setup.md](docs/environment-setup.md)
- Neo4j export/sync workflow: [specs/001-neo4j-export-sync/quickstart.md](specs/001-neo4j-export-sync/quickstart.md)
- MCP setup and troubleshooting: [MCP_GUIDE.md](MCP_GUIDE.md)
- Project assumptions and decisions: [docs/clarifying-answers.md](docs/clarifying-answers.md), [SPEC.md](SPEC.md)

MCP/LLM integration artifacts are under `llm-tooling/`:

- `llm-tooling/tool.manifest.json` is the source of truth.
- `llm-tooling/skill.md` and `llm-tooling/adapters/openai.functions.json` are generated outputs.

Regenerate MCP artifacts after manifest updates:

```bash
python llm-tooling/generate_skill_doc.py
python llm-tooling/generate_adapters.py
```

Contribution quick-start:

1. Fork the repo and create a feature branch.
2. Create a virtual environment and install dev dependencies.
3. Run tests before opening a PR.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Tests

```bash
make test
```

Direct `pytest` usage requires dev dependencies (installed by `make dev`):

```bash
pytest
```

## License

See [LICENSE](LICENSE).

## Contact

Open an issue in the repository for questions, bug reports, or feature requests.
