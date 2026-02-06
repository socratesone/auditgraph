# Feature Specification: Interfaces and UX

**Feature Branch**: `009-interfaces-ux`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Define CLI/UI scope, required commands, outputs, and editor integration"

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

### User Story 1 - CLI Command Surface (Priority: P1)

As a user, I want a clear CLI command set so I can run ingestion, extraction, linking, indexing, and queries predictably.

**Why this priority**: CLI is the primary interface for day 1.

**Independent Test**: Verify the spec lists required commands and outputs for each.

**Acceptance Scenarios**:

1. **Given** a required command (ingest, extract, link, index, query), **When** I read the spec, **Then** I can identify its inputs and outputs.
2. **Given** a CLI run, **When** I request machine output, **Then** I receive JSON with documented fields.

---

### User Story 2 - Output Formats (Priority: P2)

As a reviewer, I want consistent output formats so that results are easy to consume by humans and tools.

**Why this priority**: Output schema consistency enables automation and auditability.

**Independent Test**: Verify outputs include JSON schema definitions and human-readable summaries.

**Acceptance Scenarios**:

1. **Given** a query result, **When** I request JSON output, **Then** it conforms to documented fields.

---

### User Story 3 - Editor Integration (Priority: P3)

As a user, I want basic editor integration guidance so that links can be inserted from results in later phases.

**Why this priority**: It defines the minimum integration expectations without expanding MVP scope.

**Independent Test**: Confirm the spec states integration depth and defers deeper editor features.

**Acceptance Scenarios**:

1. **Given** an editor integration feature, **When** I read the spec, **Then** I can see it is limited to opening results and inserting links (phase 2+).

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- CLI command requested without required input paths.
- Output format flag conflicts (json + human summary).
- Editor integration requested when feature is disabled.
- CLI command name conflicts with reserved shell keywords.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The specification MUST define CLI-first interface preference and optional local web UI.
- **FR-002**: The specification MUST list required CLI commands: init, ingest, extract, link, index, query, node, neighbors, diff, export, jobs, rebuild, why-connected.
- **FR-003**: The specification MUST define machine-readable JSON output for CLI commands.
- **FR-004**: The specification MUST define human-readable summaries for CLI output.
- **FR-005**: The specification MUST define minimum editor integration depth (open results, insert links) for phase 2+.
- **FR-006**: The specification MUST define output schema fields for query results.
- **FR-007**: The specification MUST define how CLI commands report errors and non-zero exit codes.
- **FR-008**: The specification MUST define default output formats when no flag is provided.

### Key Entities *(include if feature involves data)*

- **Command**: A CLI operation with inputs, outputs, and exit codes.
- **OutputPayload**: Structured JSON response for CLI commands.
- **InterfacePolicy**: Declares CLI-first and optional UI scope.
- **IntegrationSurface**: Editor actions like open result and insert link.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of required CLI commands have documented inputs and outputs.
- **SC-002**: 100% of machine-readable outputs are JSON with documented fields.
- **SC-003**: 95% of CLI tasks can be completed without referring to external docs.
- **SC-004**: Reviewers can identify output format and editor integration depth in under 2 minutes.

## Assumptions

- CLI is the primary interface in MVP.
- Editor integration is deferred to phase 2+.
