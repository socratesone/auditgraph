# auditgraph

Auditgraph is a local-first, deterministic personal knowledge graph (PKG) toolkit for engineers.

## Current Status

This repository contains an initial CLI scaffold and workspace initializer. Core pipeline stages
(ingest, extract, link, index, query, rebuild) are present as placeholders to be implemented
in upcoming milestones.

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

See `docs/clarifying-answers.md` for the current answers to the project discovery questions and
implementation assumptions.
