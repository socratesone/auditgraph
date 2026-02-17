# auditgraph Quickstart

Get from clone to first query in a few minutes.

## Prerequisites

- Python 3.10+
- `git`

## 1) Install

```bash
git clone https://github.com/socratesone/auditgraph
cd auditgraph
python -m venv .venv
source .venv/bin/activate
pip install -e .
auditgraph version
```

Shortcut:

```bash
make dev
```

## 2) Initialize a workspace

From the repository root:

```bash
auditgraph init --root .
```

## 3) Run first pipeline

```bash
auditgraph ingest --root . --config config/pkg.yaml
```

## 4) Query your graph

```bash
auditgraph query --q "symbol" --root . --config config/pkg.yaml
```

Optional inspection commands:

```bash
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
```

## 5) Export results

```bash
auditgraph export --format json --root . --config config/pkg.yaml
```

## Common fixes

- If you see `Missing schema_version in manifest`, run:

  ```bash
  auditgraph rebuild --root . --config config/pkg.yaml
  ```

- If `auditgraph` command is not found, re-activate venv:

  ```bash
  source .venv/bin/activate
  ```

## Next docs

- Full usage and CLI reference: `README.md`
- VS Code MCP setup: `MCP_GUIDE.md`
- Environment details: `docs/environment-setup.md`
