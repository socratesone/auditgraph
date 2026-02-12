# Data Model: MCP Tools and LLM Integration

**Branch**: 016-mcp-tools-llm-integration  
**Date**: 2026-02-11  
**Spec**: [specs/016-mcp-tools-llm-integration/spec.md](spec.md)

This feature defines the data concepts used for tool manifests and adapters.

## Entities

### ToolManifest
Represents the interface-neutral source of truth.

**Fields**
- `manifest_version` (string)
- `project` (object): name, version, runtime, execution_model, entrypoint, description
- `tools` (list[ToolDefinition])

**Rules**
- Manifest is the single source of truth for generated artifacts.

---

### ToolDefinition
Defines an individual tool.

**Fields**
- `name` (string): snake_case identifier
- `title` (string)
- `description` (string)
- `risk` (string): low | medium | high
- `idempotency` (string): idempotent | non-idempotent | unknown
- `timeout_ms` (int)
- `input_schema` (object)
- `output_schema` (object)
- `error_schema` (object)
- `examples` (list[object])
- `constraints` (object)

**Rules**
- Each tool includes at least one example.
- Schemas are strict and deterministic.

---

### AdapterBundle
Represents generated interface adapters.

**Fields**
- `format` (string): mcp | openai | langchain
- `tools` (list[string])
- `generated_at` (string)

---

### SkillDoc
Represents the generated usage guide.

**Fields**
- `tool_name` (string)
- `risk` (string)
- `inputs` (list[string])
- `outputs` (list[string])
- `examples` (list[string])
