# auditgraph

Auditgraph is a local-first, deterministic personal knowledge graph (PKG) toolkit for engineers. It ingests plain-text notes and code, deterministically extracts entities and claims, creates explainable typed links, builds hybrid search indexes, and provides CLI-first navigation with optional local UI. The source of truth remains plain-text; derived artifacts are reproducible, diffable, and fully audited.

## Purpose and Scope

- Local-first, offline-capable PKG for engineers and engineering teams.
- Deterministic ingestion, extraction, linking, indexing, and query with stable IDs and audit logs.
- Source of truth is plain-text content; derived artifacts are rebuildable and versioned.
- CLI-first workflows, with optional local UI planned.
- Optional LLM-assisted extraction is supported only as a replayable, fully logged step.

## Current Status

- CLI scaffold and workspace initializer are implemented.
- Core pipeline commands (ingest, extract, link, index, query, rebuild) are present as placeholders.
- Specification is split into focused documents under docs/spec for resolving remaining decisions.

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

auditgraph ingest
```

## Project Assumptions

See docs/clarifying-answers.md for the current answers to the project discovery questions and
implementation assumptions. See [SPEC.md](SPEC.md) and the spec breakdown in [docs/spec/00-overview.md](docs/spec/00-overview.md) for the full design scope and open decisions.
