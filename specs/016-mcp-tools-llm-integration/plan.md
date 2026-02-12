# Implementation Plan: MCP Tools and LLM Integration

**Branch**: `016-mcp-tools-llm-integration` | **Date**: 2026-02-11 | **Spec**: [specs/016-mcp-tools-llm-integration/spec.md](spec.md)
**Input**: Feature specification from `/specs/016-mcp-tools-llm-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Define an interface-neutral tool manifest, MCP server, and skill doc generator for auditgraph CLI capabilities with deterministic schemas and error normalization.

## Technical Context

**Language/Version**: Python >=3.10  
**Primary Dependencies**: stdlib, pytest  
**Storage**: Generated artifacts under `llm-tooling/`  
**Testing**: pytest contract tests for tool schemas and error normalization  
**Target Platform**: Linux (x86_64), macOS (Intel/Apple Silicon)  
**Project Type**: Single Python package (`auditgraph/`)  
**Performance Goals**: MCP tool calls return within 5s for read operations  
**Constraints**: Deterministic outputs; CLI command parity; read-only enforcement  
**Scale/Scope**: CLI commands listed in tool inventory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **DRY**: Manifest is the single source of truth for MCP and adapters.
- **SOLID**: Separate manifest parsing, adapter execution, and MCP server.
- **TDD (non-negotiable)**: Contract tests precede MCP server wiring.
- **Determinism**: Manifest-driven generation is stable and reproducible.

GATE STATUS: PASS

## Project Structure

### Documentation (this feature)

```text
specs/016-mcp-tools-llm-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
auditgraph/
├── cli.py
└── utils/

llm-tooling/
├── tool.manifest.json
├── skill.md
├── mcp/
├── adapters/
└── tests/
```

**Structure Decision**: Generate LLM tooling artifacts under `llm-tooling/` while keeping core CLI in `auditgraph/`.

## Phase 0 Research

- Outputs in [specs/016-mcp-tools-llm-integration/research.md](research.md).

## Phase 1 Design

- Data model: [specs/016-mcp-tools-llm-integration/data-model.md](data-model.md).
- Contracts: [specs/016-mcp-tools-llm-integration/contracts/tool-manifest.openapi.yaml](contracts/tool-manifest.openapi.yaml).
- Quickstart: [specs/016-mcp-tools-llm-integration/quickstart.md](quickstart.md).

## Constitution Check (Post-Design)

- Manifest-driven generation and deterministic error models remain explicit.

GATE STATUS: PASS

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
