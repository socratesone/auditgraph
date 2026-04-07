# auditgraph Quickstart

Get from clone to first query in a few minutes.

## Prerequisites

- Python 3.10+
- Linux (x86_64) or macOS (Intel/Apple Silicon)
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
auditgraph ingest
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
auditgraph query --q "symbol"
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
auditgraph node <entity_id>
auditgraph neighbors <entity_id> --depth 2
```

## 4b) Browse, filter, and aggregate (no keyword required)

The `list` command browses entities directly without a search term, with filter, sort, pagination, and aggregation flags:

```bash
auditgraph list --type commit                                        # all commits
auditgraph list --type commit --where "author_email=alice@example.com"
auditgraph list --type commit --sort authored_at --desc --limit 10
auditgraph list --group-by type --count                              # entities per type
auditgraph list --count                                              # total count
```

The same filter flags work on `query` (narrows BM25 search results) and `neighbors` (filter graph traversal by edge type and confidence):

```bash
auditgraph query --q "config" --type file --limit 5
auditgraph neighbors <commit_id> --edge-type authored_by
auditgraph neighbors <entity_id> --min-confidence 0.8
```

Operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~` (contains). Numeric values like `mention_count>=5` are compared numerically; other values are compared as strings (ISO dates sort lexicographically). Multiple `--type` flags are OR'd; multiple `--where` clauses are AND'd.

## 5) Export results

```bash
auditgraph export --format json
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
auditgraph export-neo4j --output exports/neo4j/graph.cypher
```

Dry-run and live sync:

```bash
auditgraph sync-neo4j --dry-run
auditgraph sync-neo4j
```

Detailed guide: [docs/integration/neo4j.md](docs/integration/neo4j.md).

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
auditgraph rebuild
```

Or run the git provenance stage alone:

```bash
auditgraph git-provenance
```

Query file provenance:

```bash
auditgraph git-who README.md
auditgraph git-log README.md
auditgraph git-introduced README.md
auditgraph git-history README.md
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

## Optional: enable NER (named-entity extraction)

NER is off by default because it runs spaCy inference over every chunk and is meaningful only on natural-language content (notes, documents, PDFs). To enable it on a workspace that contains documents:

```bash
python -m spacy download en_core_web_sm
```

Then set `extraction.ner.enabled: true` in your profile in `config/pkg.yaml`. Re-run `auditgraph rebuild`.

Even when enabled, NER only runs on chunks whose source file is a natural-language document — by default `.md`, `.markdown`, `.txt`, `.rst`, `.pdf`, and `.docx`. Code files (`.py`, `.js`, `.ts`, etc.) and extensionless files (`Makefile`, `Dockerfile`) are skipped automatically. You can override the allowlist via `extraction.ner.natural_language_extensions` if you have custom document formats.

For code-only repositories, you can leave NER off entirely — there's nothing for it to do.

## Common fixes

- If you see `Missing schema_version in manifest`, run:

  ```bash
  auditgraph rebuild
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
- VS Code MCP setup: `docs/integration/mcp_guide.md`
- Environment details: `docs/environment-setup.md`
