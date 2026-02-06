# Spec: Interface-Agnostic LLM Tool Packaging (MCP + Skill + Adapters)

**IMPORTANT - BEFORE CREATING SPEC FROM THIS DOCUMENT**
Evaluate this document and modify it. The document in its current state is generic and is meant to build an MCP (or otherwise LLM-accessible tool) for a generic graph project, an as such lacks the specificity unique to auditgraph. Before we attempt to implement this, we **MUST** alter this specification to be in harmony with the current projects consitution and existing specifications, contracts, schemas, and CLI.

## Goal
Given an existing software project (library, CLI, service, or monolith), generate a complete “LLM-usable tool package” that supports multiple LLM tool paradigms without locking into any single one.

Primary deliverables:
- **MCP (Model Context Protocol) tool server** (or compatible MCP wrapper) exposing the project’s capabilities as tools.
- **Skill document** (a human- and model-readable usage guide) that describes what the tool does, how to call it, constraints, examples, and failure modes.
- **Interface-neutral Tool Manifest (IR)** used to generate MCP + Skill + future adapters (OpenAI tool schema, function calling, LangChain tools, etc.).

Non-goals:
- Rewriting core business logic.
- Building a full auth/permissions system unless required by the project.
- Perfect semantic understanding of arbitrary codebases without hints (the system will support hints and incremental refinement).

---

## Core Idea: Tool Interface Neutrality
Introduce a **Tool Interface IR (Intermediate Representation)** as the single source of truth.

From the IR, generate:
- MCP server (tools + schemas + handlers)
- skill.md (usage + examples + guardrails)
- optional adapters (OpenAI function schemas, JSON-RPC, CLI wrapper, etc.)

This prevents “MCP-shaped” decisions from leaking into the project and keeps future portability.

---

## Inputs
Minimum required inputs:
- Path to project root (local filesystem)
- Project type (auto-detected if possible): `library | CLI | HTTP API | mixed`
- Runtime target: `node | python | go | rust | other`
- Execution model: `in-process | subprocess | remote-http`

Optional but strongly recommended:
- “Capability hints” (what should be exposed as tools)
- Existing API docs / README / CLI help output
- Example commands / code snippets
- Auth expectations (if any)
- Safety constraints (allowed operations, read-only mode, rate limits)

---

## Outputs (Generated Artifacts)
Directory structure (example):
---
/llm-tooling/
  tool.manifest.json          # Tool Interface IR (source of truth)
  skill.md                    # Skill doc (usage guide)
  mcp/
    package.json              # if node-based MCP server
    src/
      server.ts               # MCP server entry
      tools/
        <tool>.ts             # tool definitions + handlers
      adapters/
        project.ts            # calls into project via chosen execution model
      schemas/
        <tool>.schema.json    # JSON Schemas generated from IR
    README.md                 # run instructions
  adapters/                   # optional future adapters
    openai.functions.json
    langchain.tools.ts
  tests/
    tool-contract.spec.ts     # contract tests for schemas + behavior
    golden/
      <tool>.request.json
      <tool>.response.json
---

---

## High-Level Phases

### Phase 0: Project Classification
1. Detect language/runtime (package.json, pyproject.toml, go.mod, Cargo.toml, etc.).
2. Detect capability surfaces:
   - CLI commands
   - exported library functions
   - HTTP routes (OpenAPI, router files)
   - DB migrations / data models (optional)
3. Determine best execution model:
   - **subprocess** for CLIs (lowest coupling)
   - **in-process** for libraries (highest performance)
   - **remote-http** for existing services

Output: `project.profile.json` (internal metadata; not required for users).

---

### Phase 1: Capability Discovery → Draft Tool List
Discovery strategies (use all that apply):
- Parse README / docs for verbs (“create”, “search”, “list”, “export”).
- For CLIs: run `--help` and parse command tree.
- For HTTP APIs: look for OpenAPI / routes.
- For libraries: scan exports/public entrypoints.

Then generate a draft list of candidate tools:
- Name (stable, snake_case)
- Purpose (one sentence)
- Category: `read | write | admin | analytics`
- Risk level: `low | medium | high` (writes are higher)
- Inputs/outputs (rough)

Output: `tools.draft.json` (internal).

---

### Phase 2: Tool Interface IR (Manifest) Finalization
Produce `tool.manifest.json` with:
- tool metadata
- JSON Schema input/output for each tool
- error schema
- operational constraints
- examples
- deterministic semantics

#### Tool Manifest Schema (conceptual)
---
{
  "manifest_version": "1.0",
  "project": {
    "name": "string",
    "version": "string",
    "runtime": "node|python|go|rust|other",
    "execution_model": "in-process|subprocess|remote-http",
    "entrypoint": "string",
    "description": "string"
  },
  "tools": [
    {
      "name": "snake_case_name",
      "title": "Human readable",
      "description": "What it does",
      "risk": "low|medium|high",
      "idempotency": "idempotent|non-idempotent|unknown",
      "timeout_ms": 30000,
      "input_schema": { "type": "object", "properties": { }, "required": [] },
      "output_schema": { "type": "object", "properties": { }, "required": [] },
      "error_schema": {
        "type": "object",
        "properties": {
          "code": { "type": "string" },
          "message": { "type": "string" },
          "details": { "type": "object" }
        },
        "required": ["code", "message"]
      },
      "examples": [
        {
          "input": { },
          "output": { }
        }
      ],
      "constraints": {
        "read_only_mode_supported": true,
        "side_effects": ["string"],
        "rate_limit": { "requests_per_minute": 60 },
        "allowed_paths": ["string"],
        "notes": ["string"]
      }
    }
  ]
}
---

Rules:
- Schemas must be strict (no ambiguous “any” unless unavoidable).
- Every tool must have at least one example.
- Every tool must define deterministic error codes.

---

### Phase 3: Adapter Layer Generation
Generate a uniform adapter interface:
- `invoke(toolName, input) -> output`
- Handles execution model, serialization, timeouts, retries (if allowed), logging.

Execution models:

#### A) subprocess (CLI wrapper)
- Build command line from input schema fields.
- Run process with controlled env and working directory.
- Parse stdout (json preferred; otherwise structured parse rules).
- Normalize errors (exit codes + stderr) into error_schema.

#### B) in-process (library wrapper)
- Import project module(s).
- Call function(s) mapped to tools.
- Validate input/output against schema.
- Catch exceptions and normalize.

#### C) remote-http
- Map tools to endpoints.
- Construct request from input schema.
- Handle auth and retry policies.
- Normalize HTTP errors to error_schema.

Output: `llm-tooling/mcp/src/adapters/project.*`

---

### Phase 4: MCP Server Generation
Generate an MCP server that:
- Registers tools from `tool.manifest.json`
- Exposes tool metadata and JSON Schema
- Routes tool calls to adapter `invoke()`
- Validates input/output against schema
- Produces normalized errors

MCP requirements:
- Tool list must be generated from IR (no hand-edits).
- Server must be runnable with a single command.
- Logging must include tool name, request id, duration, result status (not full payload unless explicitly enabled).

Output: `llm-tooling/mcp/*`

---

### Phase 5: Skill Document Generation (skill.md)
Generate `skill.md` from the same IR.

Required sections:
1. **What this skill does**
2. **When to use it / when not to**
3. **Available tools** (name + description + risk)
4. **Inputs/outputs** (concise + link to schemas)
5. **Examples** (copy/paste ready)
6. **Failure modes and error codes**
7. **Safety and constraints** (read-only mode, allowed paths, rate limits, timeouts)
8. **Operational notes** (setup, environment variables, auth, performance)

The skill doc must be interface-agnostic:
- It must not assume MCP only.
- It should describe tool calls conceptually and provide concrete examples for MCP plus a generic JSON call shape.

Output: `llm-tooling/skill.md`

---

### Phase 6: Contract Tests (Golden Tests)
Generate tests that:
- Validate tool schemas compile.
- Validate sample inputs pass schema.
- Validate sample outputs match schema.
- Validate error normalization rules.
- Provide golden request/response fixtures.

Output: `llm-tooling/tests/*`

---

## Cross-Cutting Concerns

### Schema Validation
- Use JSON Schema Draft 2020-12 (or explicitly chosen version).
- Validate:
  - incoming tool args
  - adapter outputs
- Reject unknown properties unless explicitly allowed.

### Deterministic Error Model
Standard error codes (minimum set):
- `INVALID_INPUT`
- `NOT_FOUND`
- `CONFLICT`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `TIMEOUT`
- `RATE_LIMITED`
- `UPSTREAM_ERROR`
- `INTERNAL_ERROR`

### Read-Only Mode
Support `READ_ONLY=1` environment variable:
- Tools tagged as write/high-risk must refuse with `FORBIDDEN` in read-only mode.

### Logging
- Structured logs (json lines) with:
  - request_id
  - tool
  - duration_ms
  - status: ok|error
  - error.code (if any)

### Security
- Subprocess: sanitize args, no shell interpolation, allowlist commands, enforce working directory, restrict file access when possible.
- Remote HTTP: do not log secrets, support token via env var.
- In-process: constrain exposed functions to a safe allowlist.

---

## Tool Design Guidelines (for Knowledge Graph Projects)
Typical tools worth exposing (examples; generate only if applicable):
- `kg_ingest_documents`
- `kg_extract_entities`
- `kg_extract_relations`
- `kg_upsert_triples`
- `kg_query_cypher` (or DSL)
- `kg_search_nodes`
- `kg_get_node`
- `kg_get_neighbors`
- `kg_explain_provenance`
- `kg_export_subgraph`

Design rules:
- Prefer high-level tasks over raw primitives (fewer tools, more value).
- Avoid “arbitrary code execution” tools.
- Provide provenance fields in outputs (`source_id`, `span`, `confidence`, etc.) if the KG supports it.

---

## Example: Generated MCP Tool Definition (Conceptual)
(Actual wire format depends on MCP SDK/runtime; this shows the intent.)
---
Tool: kg_search_nodes
Input schema:
{
  "type": "object",
  "properties": {
    "query": { "type": "string", "minLength": 1 },
    "limit": { "type": "integer", "minimum": 1, "maximum": 100, "default": 20 },
    "node_types": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["query"],
  "additionalProperties": false
}
Output schema:
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string" },
          "label": { "type": "string" },
          "score": { "type": "number" }
        },
        "required": ["id", "type", "label", "score"],
        "additionalProperties": false
      }
    }
  },
  "required": ["results"],
  "additionalProperties": false
}
---

---

## Example: Skill Doc Skeleton (Generated)
---
# Skill: <Project Name> Tooling

## What this skill does
<One paragraph describing capability surface>

## When to use it
- <bullets>

## When NOT to use it
- <bullets>

## Tools
### kg_search_nodes (risk: low)
Purpose: <...>
Inputs: query, limit, node_types
Outputs: results[]

Example call (generic):
{ "tool": "kg_search_nodes", "input": { "query": "Acme", "limit": 10 } }

Example call (MCP):
<SDK-specific example generated alongside>

## Failure modes
- INVALID_INPUT: <...>
- TIMEOUT: <...>

## Safety and constraints
- Read-only mode supported: yes
- Rate limit: 60 rpm
---

---

## Implementation Requirements
- Single-command generation:
  - `llm-toolgen init <project_path> --out llm-tooling/`
  - `llm-toolgen build` (regenerates from manifest)
- Regeneration must be stable (same inputs -> same outputs).
- Manual edits must happen in:
  - `tool.manifest.json` (source of truth)
  - optional override files (e.g., `overrides/*.json`)
Generated code should not be hand-edited.

---

## Acceptance Criteria
1. `tool.manifest.json` exists and validates against the manifest schema.
2. `skill.md` references every tool and includes at least one example per tool.
3. MCP server starts and lists all tools from the manifest.
4. Calling each tool:
   - validates input
   - invokes adapter
   - returns schema-valid output OR schema-valid error
5. Contract tests pass on CI.

---

## Extension Points (Future Adapters)
From the same manifest, optionally generate:
- OpenAI function calling JSON schema bundle
- LangChain tool wrappers
- “Skills” format variants for other runtimes
- OpenAPI facade for tools (HTTP gateway)

Key rule: adapters consume the IR; the project does not depend on adapters.
