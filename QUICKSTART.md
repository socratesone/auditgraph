# auditgraph Quickstart

Get from clone to first query in a few minutes.

## Prerequisites

- Python 3.10+
- Linux (x86_64) or macOS (Intel/Apple Silicon) for day-1 support
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

Expected result (shape):

```json
{
  "stage": "ingest",
  "status": "ok",
  "detail": {
    "files": 1,
    "manifest": ".pkg/profiles/default/runs/<run_id>/ingest-manifest.json",
    "profile": "default",
    "ok": 1,
    "skipped": 0,
    "failed": 0
  }
}
```

## 4) Query your graph

```bash
auditgraph query --q "symbol" --root . --config config/pkg.yaml
```

Expected result (shape):

```json
{
  "query": "symbol",
  "results": [
    {
      "id": "ent_...",
      "score": 1.0,
      "explanation": {
        "matched_terms": ["symbol"],
        "bm25_score": 1.0,
        "semantic_score": 0.0,
        "graph_boost": 0.0,
        "tie_break": ["ent_..."]
      }
    }
  ]
}
```

Entity matching is case-insensitive exact-key lookup against indexed names and aliases.
Chunk matching is case-insensitive substring matching.

Example: `"auth_token"` matches entities indexed as `auth_token` and chunks containing `auth_token` text.

Markdown sub-entity extraction (`ag:section`, `ag:technology`, `ag:reference`) is planned but not enabled in the default pipeline yet.

Optional inspection commands:

```bash
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
```

## 5) Export results

```bash
auditgraph export --format json --root . --config config/pkg.yaml
```

## 6) Export/sync with Neo4j (optional)

Set connection values:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="<your_password>"
export NEO4J_DATABASE="neo4j"
```

Export Neo4j Cypher:

```bash
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/graph.cypher
```

Dry-run and live sync:

```bash
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

Detailed guide: `specs/001-neo4j-export-sync/quickstart.md`.

## 7) Git provenance (optional)

Enable git history ingestion by adding to `config/pkg.yaml`:

```yaml
profiles:
  default:
    git_provenance:
      enabled: true
```

Run ingestion (requires a prior `ingest` run):

```bash
auditgraph rebuild --root . --config config/pkg.yaml
```

Or run the git provenance stage alone:

```bash
auditgraph git-provenance --root . --config config/pkg.yaml
```

Query file provenance:

```bash
auditgraph git-who README.md --root .
auditgraph git-log README.md --root .
auditgraph git-introduced README.md --root .
auditgraph git-history README.md --root .
```

Optional tuning in `config/pkg.yaml`:

```yaml
    git_provenance:
      enabled: true
      max_tier2_commits: 1000
      hot_paths: ["pyproject.toml", "package.json"]
      cold_paths: ["*.lock", "*.generated.*"]
```

Detailed guide: `specs/020-git-provenance-ingestion/quickstart.md`.

## Common fixes

- If you see `Missing schema_version in manifest`, run:

  ```bash
  auditgraph rebuild --root . --config config/pkg.yaml
  ```

- If `auditgraph` command is not found, re-activate venv:

  ```bash
  source .venv/bin/activate
  ```

- If config loading fails with a PyYAML error, install dependencies with:

  ```bash
  make dev
  ```

## Next docs

- Full usage and CLI reference: `README.md`
- VS Code MCP setup: `MCP_GUIDE.md`
- Environment details: `docs/environment-setup.md`
