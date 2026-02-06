# Environment Setup

This project uses a local virtual environment and `pyproject.toml` for dependencies.
The steps below create a `.venv` and document how to produce a requirements file
for a custom environment.

## Prerequisites

- Python 3.10+ (see `pyproject.toml`)
- `pip` (bundled with most Python installs)

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

## Optional Dependencies

Install optional tools as needed:

```bash
pip install pyyaml pytest
```

Notes:
- `pyyaml` is required if you want to load YAML config files.
- `pytest` is required to run the test suite.

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
