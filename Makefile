.PHONY: venv dev test

venv:
	@test -d .venv || python -m venv .venv
	@.venv/bin/python -m pip install --upgrade pip setuptools wheel


dev: venv
	@.venv/bin/pip install -r requirements-dev.txt

test: dev
	@.venv/bin/pytest
