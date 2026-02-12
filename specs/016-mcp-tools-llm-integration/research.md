# Research: MCP Tools and LLM Integration

**Branch**: 016-mcp-tools-llm-integration  
**Date**: 2026-02-11  
**Spec**: [specs/016-mcp-tools-llm-integration/spec.md](spec.md)

This document captures implementation-relevant decisions for auditgraph MCP tooling and adapters.

## Decisions

### Decision 1: Capability surface
- **Decision**: Map tools directly to existing auditgraph CLI commands.
- **Rationale**: Maintains parity with current functionality and avoids duplicating business logic.
- **Alternatives considered**:
  - In-process library calls (rejected because CLI is the stable interface today).

### Decision 2: Execution model
- **Decision**: Use subprocess execution with strict argument allowlists.
- **Rationale**: Lowest coupling and keeps tools aligned with CLI behavior.
- **Alternatives considered**:
  - Remote HTTP adapter (rejected because no service API exists).

### Decision 3: Read-only enforcement
- **Decision**: Use `READ_ONLY=1` to block write and high-risk tools.
- **Rationale**: Consistent with spec and safety constraints.
- **Alternatives considered**:
  - Per-tool config flags (rejected for simplicity in the initial release).

### Decision 4: Generated artifacts location
- **Decision**: Store MCP tooling under `llm-tooling/` at repo root.
- **Rationale**: Keeps generated artifacts separate from core CLI code.
- **Alternatives considered**:
  - Embedding inside `auditgraph/` (rejected to avoid mixing generated and manual code).
