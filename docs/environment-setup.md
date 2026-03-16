# Environment Setup

This project uses a local virtual environment and `pyproject.toml` for dependencies.
The steps below create a `.venv` and document how to produce a requirements file
for a custom environment.

## Prerequisites

- Python 3.10+ (see `pyproject.toml`)
- `pip` (bundled with most Python installs)
- Supported OS targets: Linux (x86_64) and macOS (Intel/Apple Silicon); Windows is not supported for day 1.

## Create and Activate `.venv`

Makefile shortcut (recommended):

```bash
make dev
```

Manual setup:

```bash
python -m venv .venv
source .venv/bin/activate
```

Upgrade packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Install the project in editable mode:

```bash
pip install -e .
```

Notes:
- `make venv` creates the virtual environment and upgrades packaging tools.
- `make dev` installs the development requirements from `requirements-dev.txt`.
- `make test` runs the test suite using the virtual environment.

## Jobs Configuration

Automation jobs are configured in `config/jobs.yaml` and read by `auditgraph jobs list` and `auditgraph jobs run`.

## Optional Dependencies

Install optional tools as needed:

```bash
pip install pyyaml pytest pypdf python-docx
```

Notes:
- `pyyaml` is required if you want to load YAML config files.
- `pytest` is required to run the test suite.
- `pypdf` is required for PDF text-layer extraction.
- `python-docx` is required for DOCX paragraph extraction.

## Neo4j Environment (Optional)

## Document Ingestion Config Keys

`config/pkg.yaml` supports day-1 document ingestion keys under `profiles.<name>.ingestion`:

- `allowed_extensions`: include `.pdf` and `.docx`
- `ocr_mode`: `off` (default), `auto`, or `on`
- `chunk_tokens`: token window size for chunking
- `chunk_overlap_tokens`: overlap size between consecutive chunks
- `max_file_size_bytes`: file-size guardrail for parser execution

For Neo4j export/sync workflows, set:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="<your_password>"
export NEO4J_DATABASE="neo4j"
```

Common commands:

```bash
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/graph.cypher
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
auditgraph sync-neo4j --root . --config config/pkg.yaml
```

Import exported Cypher with `cypher-shell`:

```bash
cat exports/neo4j/graph.cypher | cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"
```

## MCP Subprocess PATH Configuration

The MCP server invokes the `auditgraph` CLI as a subprocess. When the server is launched
by an editor or tool (VS Code, Claude Code), the subprocess inherits the server's environment.
Since `auditgraph` is installed inside the virtual environment, `PATH` must include the
venv `bin` directory for subprocess invocation to succeed.

Always include a `PATH` entry in the MCP `env` configuration:

```json
"env": {
  "PATH": "/path/to/auditgraph/.venv/bin:/usr/local/bin:/usr/bin:/bin"
}
```

Without this, MCP tool calls will fail with `[Errno 2] No such file or directory: 'auditgraph'`.

See [MCP_GUIDE.md](../MCP_GUIDE.md) for full configuration examples.

## Requirements Files (Optional)

If you want a pinned requirements file for a custom environment, generate one
from your active `.venv`:

```bash
pip freeze > requirements-dev.txt
```

You can recreate the environment later with:

```bash
pip install -r requirements-dev.txt
```

This repository uses `pyproject.toml` as the source of truth, so a requirements
file is optional and intended for local or deployment-specific workflows.
