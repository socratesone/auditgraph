.PHONY: venv dev test setup lint format typecheck clean

venv:
	@test -d .venv || python -m venv .venv
	@.venv/bin/python -m pip install --upgrade pip setuptools wheel

dev: venv
	@.venv/bin/pip install -r requirements-dev.txt

setup: dev
	@echo "Running smoke test..."
	@.venv/bin/python -c "import auditgraph; print(f'auditgraph {auditgraph.__version__} installed')"
	@echo "Setup complete."

test: dev
	@.venv/bin/pytest

lint:
	@.venv/bin/ruff check auditgraph/ tests/

format:
	@.venv/bin/black --check auditgraph/ tests/

typecheck:
	@.venv/bin/mypy auditgraph/

clean:
	@rm -rf .venv build dist *.egg-info .mypy_cache .ruff_cache .pytest_cache
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
