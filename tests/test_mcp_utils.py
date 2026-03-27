"""Tests for MCP utility modules: errors, inventory, manifest."""
from __future__ import annotations

import pytest

from auditgraph.utils.mcp_errors import ERROR_CODES, normalize_error
from auditgraph.utils.mcp_inventory import ALL_TOOLS, READ_TOOLS, WRITE_TOOLS


class TestNormalizeError:
    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_valid_code_preserved(self, code: str) -> None:
        result = normalize_error(code, "test message")
        assert result["code"] == code

    def test_unknown_code_falls_back_to_internal_error(self) -> None:
        result = normalize_error("BOGUS_CODE", "something went wrong")
        assert result["code"] == "INTERNAL_ERROR"

    def test_message_is_included(self) -> None:
        result = normalize_error("NOT_FOUND", "item missing")
        assert result["message"] == "item missing"

    def test_detail_included_when_provided(self) -> None:
        result = normalize_error("NOT_FOUND", "missing", detail="id=42")
        assert result["detail"] == "id=42"

    def test_detail_absent_when_not_provided(self) -> None:
        result = normalize_error("NOT_FOUND", "missing")
        assert "detail" not in result

    def test_detail_absent_when_none(self) -> None:
        result = normalize_error("NOT_FOUND", "missing", detail=None)
        assert "detail" not in result


class TestMcpInventory:
    def test_all_tools_is_union_of_read_and_write(self) -> None:
        assert set(ALL_TOOLS) == set(READ_TOOLS) | set(WRITE_TOOLS)

    def test_no_overlap_between_read_and_write(self) -> None:
        overlap = set(READ_TOOLS) & set(WRITE_TOOLS)
        assert overlap == set(), f"Unexpected overlap: {overlap}"

    def test_all_tools_length(self) -> None:
        assert len(ALL_TOOLS) == len(READ_TOOLS) + len(WRITE_TOOLS)


class TestValidateManifest:
    def test_validate_manifest_on_well_formed_manifest(self) -> None:
        """If the real manifest and contract files exist, validation should pass."""
        from auditgraph.utils.mcp_manifest import load_manifest, manifest_path, validate_manifest

        mp = manifest_path()
        if not mp.exists():
            pytest.skip("manifest file not present")

        manifest = load_manifest(mp)
        errors = validate_manifest(manifest)
        assert errors == [], f"Validation errors: {errors}"
