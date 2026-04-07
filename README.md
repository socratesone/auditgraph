![auditgraph](docs/img/auditgraph-hero.png)

# auditgraph

Local-first, deterministic personal knowledge graph tooling for engineers.

[![License](https://img.shields.io/badge/license-SEE%20LICENSE-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-enabled-brightgreen)](docs/integration/mcp_guide.md)

Auditgraph ingests plain-text notes, code, and `.pdf`/`.docx` documents, deterministically extracts entities and claims, builds explainable links, and provides CLI-first navigation. Your source of truth stays in plain text; derived artifacts are reproducible, diffable, and fully audited.

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
- [Git Provenance](#git-provenance)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Developer Docs](#developer-docs)
- [Tests](#tests)
- [License](#license)

## Features

- Local-first, offline-capable PKG for engineers and teams.
- Deterministic ingestion, extraction, linking, indexing, and query with stable IDs.
- Core document ingestion for `.pdf` and `.docx` with deterministic chunking and metadata-only citations.
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
| File ingestion (text, markdown, documents) | Implemented | Deterministic with stable IDs. Source code files are not ingested — see "Content extraction" below. |
| PDF/DOCX ingestion | Implemented | OCR mode: off/auto/on |
| Entity extraction | Implemented | Notes (markdown). Source code files are not ingested. File entities (one per path in git history) are produced by the git provenance stage when enabled. |
| NER entity extraction | Implemented | Opt-in (off by default). Requires `spacy` + a model; enable via config. Best on natural-language content, not code. |
| Linking (co-occurrence) | Implemented | Explainable links with provenance |
| BM25 keyword index | Implemented | Case-insensitive exact-key lookup |
| Query and search | Implemented | Entity + chunk matching |
| Local query filters & aggregation | Implemented | `list` command, `--type`/`--where`/`--sort`/`--limit`/`--count`/`--group-by` on `query` and `list`; edge-type and confidence filters on `neighbors` |
| Run diff | Implemented | Structural diff of ingest manifests |
| Subgraph export (JSON/DOT/GraphML) | Implemented | With budget checks and path safety |
| Neo4j export/sync | Implemented | Cypher export + live database sync |
| Jobs automation | Implemented | YAML-configured job runner |
| Pipeline replay | Implemented | Re-run from stored config snapshots |
| Schema versioning | Implemented | `v1` with compatibility checks |
| Markdown sub-entities | Planned | Code exists but not wired into pipeline |
| Semantic/vector search | Planned | Index stub only; no embeddings yet |
| Git provenance ingestion | Implemented | Commit history, authors, file lineage, MCP tools |
| LLM-assisted extraction | In Progress | Interface + NullProvider implemented; no concrete provider yet |
| Local UI | Planned | CLI-only for now |

## Installation

Prerequisites:

- Python 3.10+
- Linux (x86_64) or macOS (Intel/Apple Silicon)
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

Note: the default config (`config/pkg.yaml`) looks for `notes/` and `repos/` subdirectories via `include_paths`. Running against `examples/sample_docs/` directly requires either passing a config that sets `include_paths: ["."]`, or using `auditgraph ingest --root . --config config/pkg.yaml` from a workspace root that contains those directories.

Or run individual stages:

```bash
auditgraph ingest
auditgraph query --q "symbol"
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

### Filtering, sorting, and aggregation

Both `auditgraph query` and `auditgraph list` support filtering, sorting, pagination, and aggregation against the local `.pkg` storage — no external database required. The `list` command browses entities without needing a search keyword:

```bash
auditgraph list --type commit                                       # all commits
auditgraph list --type commit --where "author_email=alice@example.com"
auditgraph list --type commit --sort authored_at --desc --limit 10  # 10 most recent
auditgraph list --group-by type --count                             # entities per type
auditgraph neighbors <id> --edge-type authored_by --min-confidence 0.8
```

Filter operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~` (substring contains). Numeric values are auto-detected. On array fields (`aliases`, `parent_shas`), `=` checks membership and `~` checks substring across elements. Sort order is deterministic with a stable tiebreaker on `entity.id`.

### Content extraction

Current extract stage behavior:

- Creates note entities from markdown files.
- **Source code files are not ingested.** Files with extensions `.py`, `.js`, `.ts`, `.tsx`, `.jsx` are skipped at the ingest stage with reason `unsupported_extension`. Auditgraph is a documents + provenance tool; code structure navigation is better served by language-aware tools (LSP, ctags, ripgrep, treesitter-based analyzers). The decision is documented in `specs/025-remove-code-extraction/spec.md`.
- File entities are produced by the git provenance stage (one per distinct file path in commit history) when `git_provenance.enabled: true`. They serve as provenance anchors for `modifies` links from commits — every committed file, including markdown notes, PDFs, configs, and code, becomes a reachable node in the graph regardless of whether it would otherwise be ingested.
- Extracts NER entities from chunks when `profiles.<name>.extraction.ner.enabled: true`. **NER is off by default** because it runs spaCy inference over every chunk in the workspace and is meaningful only on natural-language content (notes, documents, PDFs). To enable NER, install the model with `python -m spacy download en_core_web_sm` and then set `enabled: true` in your profile's `extraction.ner` config. Even when enabled, NER only runs on chunks whose source file is a natural-language document — by default that means `.md`, `.markdown`, `.txt`, `.rst`, `.pdf`, and `.docx`. The list is configurable via `extraction.ner.natural_language_extensions` if you need to add or restrict file types.

#### NER quality limitations on technical content

The default model `en_core_web_sm` is trained on news and web text. On technical or scientific content (research papers, ML literature, domain-specific writing) it produces a high false-positive rate: technical acronyms (`GPU`, `CPU`, `RNN`, `WER`) get classified as `ner:org`; concept words (`Edge`, `Training`, `Bias`) and model names (`Whisper`, `NeMo`) get classified as `ner:person`; numeric markdown citation tokens get classified as `ner:money`. If your content is technical, expect NER output to need manual filtering or post-processing before it's useful, or consider using a domain-tuned model. SciSpaCy's `en_core_sci_sm` is a better fit for biomedical/scientific text and can be installed alongside spaCy and selected via the `extraction.ner.model` config field.

Planned markdown sub-entities (implemented in extractor code but not wired into the default extract pipeline yet):

- **`ag:section`** — one entity per heading (`# Heading` through `###### Heading`), with the heading level and source line recorded.
- **`ag:technology`** — one entity per recognized technology mention (languages, frameworks, databases, tools). Over 80 technologies are recognized including Python, Neo4j, FastAPI, React, Docker, etc.
- **`ag:reference`** — one entity per markdown link (`[text](url)`), with the URL stored in aliases and metadata.

Note: these planned markdown sub-entities are not produced by default in the current pipeline.

Document ingestion defaults:

- OCR mode defaults to `off` (supported values: `off|auto|on`).
- `.doc` is rejected in the current scope with explicit machine-readable reasons.
- Chunk citations are returned as metadata fields (`source_path`, page/paragraph location), not inline markers.

## Troubleshooting

- If you see `Missing schema_version in manifest`, run:

	```bash
	auditgraph rebuild
	```

- If `auditgraph` command is not found, re-activate your venv:

	```bash
	source .venv/bin/activate
	```

- If config loading fails due to missing YAML support, install dev dependencies:

	```bash
	make dev
	```

- If `auditgraph rebuild` appears to take much longer than expected (e.g., minutes on a small workspace), check whether NER is enabled. NER runs spaCy inference over every chunk and is intentionally off by default. Disable it in your profile's `extraction.ner.enabled` setting if you don't need named-entity extraction.

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
auditgraph export-neo4j --output exports/neo4j/graph.cypher
```

Dry-run sync (no DB mutation):

```bash
auditgraph sync-neo4j --dry-run
```

Live sync:

```bash
auditgraph sync-neo4j
```

For full setup and validation workflow, see [docs/integration/neo4j.md](docs/integration/neo4j.md).

## Git Provenance

Auditgraph can ingest local Git history to build provenance links between files and their commit, author, and branch context. Enable it in your profile config:

```yaml
profiles:
  default:
    git_provenance:
      enabled: true
      max_tier2_commits: 1000
```

Run as part of a full rebuild or standalone:

```bash
auditgraph rebuild
auditgraph git-provenance
```

Query commands:

```bash
auditgraph git-who src/auth.py            # Authors who changed a file
auditgraph git-log src/auth.py            # Commits that touched a file
auditgraph git-introduced src/auth.py     # Earliest commit for a file
auditgraph git-history src/auth.py        # Combined provenance summary
```

For configuration details (hot/cold paths, commit selection tiers), see [specs/020-git-provenance-ingestion/quickstart.md](specs/020-git-provenance-ingestion/quickstart.md).

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
auditgraph ingest
auditgraph import <path> [<path> ...]              # Manually import specific files or directories
auditgraph normalize --run-id <run_id>
auditgraph extract --run-id <run_id>
auditgraph link --run-id <run_id>
auditgraph index --run-id <run_id>
auditgraph rebuild
auditgraph query --q "symbol" [--type T] [--where "f=v"] [--sort F] [--limit N]
auditgraph list [--type T] [--where "f=v"] [--sort F] [--limit N] [--count] [--group-by F]
auditgraph node <entity_id>
auditgraph neighbors <entity_id> --depth 2 [--edge-type T] [--min-confidence X]
auditgraph why-connected --from <entity_id> --to <entity_id>
auditgraph diff --run-a <run_id_1> --run-b <run_id_2>
auditgraph export --format json
auditgraph export-neo4j --output exports/neo4j/graph.cypher
auditgraph sync-neo4j --dry-run
auditgraph replay <run_id>                         # Replay a previous run
auditgraph git-provenance                          # Ingest git history
auditgraph git-who <file>
auditgraph git-log <file>
auditgraph git-introduced <file>
auditgraph git-history <file>
auditgraph jobs list
```

For the full command surface, run `auditgraph --help`.

## Developer Docs

Documentation map:

- First-success walkthrough with expected output: [QUICKSTART.md](QUICKSTART.md)
- Environment and platform details: [docs/environment-setup.md](docs/environment-setup.md)
- Neo4j export/sync workflow: [docs/integration/neo4j.md](docs/integration/neo4j.md)
- MCP setup and troubleshooting: [docs/integration/mcp_guide.md](docs/integration/mcp_guide.md)

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

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for the full text.
