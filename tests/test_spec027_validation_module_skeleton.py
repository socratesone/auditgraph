"""Spec 027 FR-005 — llm-tooling/mcp/validation.py module skeleton check.

`llm-tooling/` contains a dash so it isn't a regular Python package.
Tests load the module via importlib (matching the existing pattern in
`llm-tooling/tests/test_mcp_server.py`).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_validation_module():
    repo_root = Path(__file__).resolve().parents[1]
    validation_path = repo_root / "llm-tooling" / "mcp" / "validation.py"
    assert validation_path.exists(), f"validation.py missing at {validation_path}"
    spec = importlib.util.spec_from_file_location("mcp_validation_spec027", validation_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_max_string_length_constant():
    mod = _load_validation_module()
    assert hasattr(mod, "DEFAULT_MAX_STRING_LENGTH")
    assert mod.DEFAULT_MAX_STRING_LENGTH == 4096


def test_validation_failed_is_exception_subclass():
    mod = _load_validation_module()
    assert hasattr(mod, "ValidationFailed")
    assert issubclass(mod.ValidationFailed, Exception)
    # Must expose a to_envelope method
    assert callable(getattr(mod.ValidationFailed, "to_envelope", None))


def test_validate_function_exists_and_callable():
    mod = _load_validation_module()
    assert hasattr(mod, "validate")
    assert callable(mod.validate)
