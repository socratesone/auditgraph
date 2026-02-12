# Feature Specification: MCP Tools and LLM Integration

**Feature Branch**: `016-mcp-tools-llm-integration`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "See 016-mcp-tools-llm-integration.md for details. spec/branch number 016."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Interface-neutral tool manifest (Priority: P1)

As an engineer, I can generate a tool manifest that maps auditgraph CLI capabilities into stable, interface-agnostic tools.

**Why this priority**: The manifest is the single source of truth that drives MCP, skills, and adapters.

**Independent Test**: Can be fully tested by validating the manifest schema, tool list, and examples.

**Acceptance Scenarios**:

1. **Given** the manifest, **When** I validate it, **Then** every tool has strict input/output schemas and examples.
2. **Given** an auditgraph CLI command, **When** I review the manifest, **Then** there is a matching tool definition.

---

### User Story 2 - MCP server for auditgraph tools (Priority: P2)

As an engineer, I can run an MCP server that exposes auditgraph tools with deterministic outputs and normalized errors.

**Why this priority**: MCP is the primary tool interface for LLM integrations.

**Independent Test**: Can be fully tested by starting the server and invoking each tool with valid and invalid inputs.

**Acceptance Scenarios**:

1. **Given** the MCP server, **When** I list tools, **Then** all manifest tools are exposed.
2. **Given** invalid input, **When** I call a tool, **Then** the server returns a normalized error code and message.

---

### User Story 3 - Skill doc and adapters (Priority: P3)

As a stakeholder, I can read a skill document and use adapter outputs without MCP lock-in.

**Why this priority**: Skills and adapters ensure portability and consistent usage guidance.

**Independent Test**: Can be fully tested by validating skill doc sections and adapter schemas against the manifest.

**Acceptance Scenarios**:

1. **Given** the skill doc, **When** I review it, **Then** each tool has at least one example and listed constraints.
2. **Given** an adapter schema bundle, **When** I compare it to the manifest, **Then** it matches tool definitions.

---


### Edge Cases

- When auditgraph is not installed in the execution environment, the tool returns a normalized `UPSTREAM_ERROR`.
- When read-only mode is enabled, write or high-risk tools return `FORBIDDEN` without side effects.
- When the manifest changes, generated artifacts are regenerated deterministically from the manifest.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool manifest MUST be the single source of truth for MCP, skill doc, and adapters.
- **FR-002**: Each tool MUST map to an existing auditgraph CLI command.
- **FR-003**: Tool schemas MUST be strict, with examples and deterministic error codes.
- **FR-004**: Read-only mode MUST block write or high-risk tools and return `FORBIDDEN`.
- **FR-005**: Tool execution MUST enforce the same path constraints as the CLI (e.g., exports under `exports/`).
- **FR-006**: Generated artifacts MUST be reproducible from identical inputs and manifest.
- **FR-007**: Skill documentation MUST list tools, risks, inputs, outputs, examples, and constraints.
- **FR-008**: Contract tests MUST validate schema compliance and error normalization.

### Non-Functional Requirements

- **NFR-001**: Read operations MUST complete within $5s$ under normal workloads (single-node execution, warm cache, and datasets up to $10^5$ nodes).
- **NFR-002**: Tool execution logs MUST be emitted for every invocation.

### Auditgraph Tool Inventory

- **Read tools**: `auditgraph version`, `query`, `node`, `neighbors`, `diff`, `jobs list`, `why-connected`.
- **Write tools**: `init`, `ingest`, `import`, `normalize`, `extract`, `link`, `index`, `rebuild`, `export`, `jobs run`.

### Tool Manifest Requirements

- Tool names are stable snake_case identifiers (e.g., `ag_query`, `ag_export`).
- Each tool includes input schema, output schema, error schema, and at least one example.
- Each tool includes `risk` and `idempotency` classification.

### Error Model

- Minimum error codes: `INVALID_INPUT`, `NOT_FOUND`, `CONFLICT`, `UNAUTHORIZED`, `FORBIDDEN`, `TIMEOUT`, `RATE_LIMITED`, `UPSTREAM_ERROR`, `INTERNAL_ERROR`.

### Read-Only Mode

- `READ_ONLY=1` forces write tools to return `FORBIDDEN` with no side effects.

### Logging Requirements

- Tool execution logs include request ID, tool name, duration, and status.

### Key Entities *(include if feature involves data)*

- **ToolManifest**: Interface-neutral source of truth for tools and schemas.
- **ToolDefinition**: A single tool with name, schemas, risk, examples, and constraints.
- **AdapterBundle**: Generated schemas for external tool interfaces.
- **SkillDoc**: Usage guide generated from the manifest.
- **ContractTest**: Golden request/response fixtures for tool validation.

### Assumptions

- Auditgraph CLI commands remain the primary capability surface.
- Optional LLM extraction remains a replayable, deterministic step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of CLI commands in scope have corresponding tool definitions.
- **SC-002**: 100% of tools include strict schemas and at least one example.
- **SC-003**: MCP server lists all tools from the manifest and returns normalized errors.
- **SC-004**: Read-only mode blocks all write tools in 100% of contract tests.
- **SC-005**: 95% of read tool calls complete within $5s$ in contract tests.
- **SC-006**: 100% of tool invocations emit logs with request ID, tool name, duration, and status in tests.
