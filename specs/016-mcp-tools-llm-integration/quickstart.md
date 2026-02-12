# Quickstart: MCP Tools and LLM Integration

**Branch**: 016-mcp-tools-llm-integration  
**Date**: 2026-02-11  
**Spec**: [specs/016-mcp-tools-llm-integration/spec.md](spec.md)

This quickstart describes the intended workflow for generating MCP tooling artifacts.

## 1) Review the manifest

Confirm tool definitions match auditgraph CLI commands and include examples, risks, and idempotency.

## 2) Generate MCP tooling

Generate artifacts from the manifest under `llm-tooling/`.

## 3) Run contract tests

Validate schema compliance, normalized errors, read-only enforcement, and path constraints with contract tests.

## 4) Verify logging and performance

Confirm each tool invocation emits a request ID, tool name, duration, and status, and read operations complete within $5s$ under normal workloads.
