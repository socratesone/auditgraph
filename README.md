# Auditgraph

![auditgraph](docs/assets/auditgraph-hero.png)

Auditgraph is a local-first, deterministic personal knowledge graph (PKG) toolkit for engineers. It ingests plain-text notes and code, deterministically extracts entities and claims, creates explainable typed links, builds hybrid search indexes, and provides CLI-first navigation with optional local UI. The source of truth remains plain-text; derived artifacts are reproducible, diffable, and fully audited.

## Purpose and Scope

- Local-first, offline-capable PKG for engineers and engineering teams.
- Deterministic ingestion, extraction, linking, indexing, and query with stable IDs and audit logs.
- Source of truth is plain-text content; derived artifacts are rebuildable and versioned.
- CLI-first workflows, with optional local UI planned.
- Optional LLM-assisted extraction is supported only as a replayable, fully logged step.

## Current Status

- CLI scaffold and workspace initializer are implemented.
- Implemented: ingest, query, node, neighbors, diff, export, jobs (basic functionality).
- Placeholders remain: extract, link, index (full pipeline still in progress).
- Specification is split into focused documents under docs/spec for resolving remaining decisions.

## Day-1 Ingestion Scope

- Supported: Markdown, plain text, Git working tree files
- Not supported (day 1): PDFs, DOCX, HTML, org-mode, email exports, issue tracker exports
- Capture channels: manual import and directory scan only (no file watchers or editor plugins)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

auditgraph init --root .
```

## CLI

```bash
auditgraph version

auditgraph init --root .

auditgraph ingest --root . --config config/pkg.yaml

auditgraph import docs/notes.md logs/ --root . --config config/pkg.yaml

auditgraph query --q "symbol" --root . --config config/pkg.yaml
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
auditgraph diff --run-a <run_id> --run-b <run_id> --root . --config config/pkg.yaml
auditgraph export --format json --root . --config config/pkg.yaml
auditgraph jobs list
auditgraph jobs run daily_digest --root . --config config/pkg.yaml
```

## Project Assumptions

See docs/clarifying-answers.md for the current answers to the project discovery questions and
implementation assumptions. See [SPEC.md](SPEC.md) and the spec breakdown in [docs/spec/00-overview.md](docs/spec/00-overview.md) for the full design scope and open decisions.
