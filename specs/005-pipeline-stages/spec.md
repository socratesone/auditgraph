# Feature Specification: Pipeline Stages Definition

**Feature Branch**: `005-pipeline-stages`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Define pipeline stage contracts, manifest schemas, and atomicity/recovery rules"

## Clarifications

### Session 2026-02-05

- Q: What is the atomic write strategy for stage artifacts and manifests? → A: Write artifacts to temp paths, then atomically rename/move into place; write the manifest last.
- Q: How are stage dependencies validated before execution? → A: Require upstream manifests for the same run_id before stage execution.

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

### User Story 1 - Stage Contracts (Priority: P1)

As a product owner, I want each pipeline stage to have a clear contract so that teams know what inputs are required and what artifacts are produced.

**Why this priority**: Stage contracts are the foundation for coordination, implementation, and verification.

**Independent Test**: Can be fully tested by reviewing the spec and confirming every stage has defined inputs, outputs, and entry/exit criteria.

**Acceptance Scenarios**:

1. **Given** the pipeline definition, **When** I inspect any stage, **Then** I can identify its required inputs, expected outputs, and manifest location.
2. **Given** a proposed change to a stage, **When** I compare contracts, **Then** I can determine compatibility with upstream and downstream stages.

---

### User Story 2 - Manifest Schemas (Priority: P2)

As a reviewer, I want each stage to define a manifest schema so that outputs can be verified, diffed, and audited consistently.

**Why this priority**: Manifest schemas enable deterministic auditing and support automation workflows.

**Independent Test**: Can be fully tested by verifying that each stage lists required manifest fields and versioning rules.

**Acceptance Scenarios**:

1. **Given** a stage manifest, **When** I read the schema, **Then** I can determine required fields and their meanings.

---

### User Story 3 - Atomicity and Recovery Rules (Priority: P3)

As an operator, I want atomicity and recovery rules documented so that failed runs can be safely retried without corrupting artifacts.

**Why this priority**: Recovery rules protect the integrity of the artifact store and ensure trust in the pipeline.

**Independent Test**: Can be fully tested by confirming the spec documents write ordering, atomic move steps, and recovery outcomes for each stage.

**Acceptance Scenarios**:

1. **Given** a stage failure mid-write, **When** I consult the spec, **Then** I can determine which artifacts are safe to keep and which must be rebuilt.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Stage input directory is missing or empty.
- Manifest write succeeds but artifact write fails (or vice versa).
- A stage is rerun with identical inputs and config.
- An unexpected stage name is requested.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The specification MUST define stage boundaries for ingest, normalize, extract, link, index, and serve.
- **FR-002**: Each stage contract MUST list required inputs, produced outputs, and artifact locations.
- **FR-003**: Each stage MUST define a manifest schema with required fields and versioning rules.
- **FR-004**: Manifest fields MUST include stage name, run identifier, input hash, output hash, config hash, status, and timestamps.
- **FR-005**: The specification MUST define atomic write behavior for manifests and artifacts, using temp paths, atomic rename/move into place, and writing the manifest last.
- **FR-006**: The specification MUST define recovery behavior for partial writes, including discarding temp artifacts and rebuilding when the manifest is missing.
- **FR-007**: The specification MUST define idempotency expectations for reruns with identical inputs and config.
- **FR-008**: The specification MUST validate stage dependencies by requiring upstream manifests for the same run_id before execution.

## Stage Contract Summary

Stages covered: ingest, normalize, extract, link, index, serve.

Each stage contract documents:
- Purpose
- Required inputs
- Produced outputs
- Entry criteria
- Exit criteria
- Manifest path

Canonical stage definitions live in [docs/spec/05-pipeline-stages.md](docs/spec/05-pipeline-stages.md).

## Atomicity and Recovery Summary

- Artifacts are written to temp paths, then atomically renamed/moved into place.
- Manifests are written last as completion signals.
- Missing manifest means discard temp artifacts and rerun the stage.

### Key Entities *(include if feature involves data)*

- **Stage Contract**: Describes a stage name, inputs, outputs, and entry/exit criteria.
- **Stage Manifest**: A structured record of a stage run, including required fields and version.
- **Run**: A single pipeline execution with a stable identifier and related manifests.
- **Artifact**: A file or directory produced by a stage and referenced by its manifest.
- **Recovery Rule**: A documented action for handling partial or failed stage outputs.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of defined stages include documented inputs, outputs, and manifest location.
- **SC-002**: 100% of stage manifests list required fields and a version identifier.
- **SC-003**: For each stage, at least one recovery path is documented for interrupted writes.
- **SC-004**: Reviewers can answer pipeline contract questions (inputs/outputs/atomicity) in under 5 minutes using the spec.

## Assumptions

- The initial scope covers ingest, normalize, extract, link, index, and serve stages only.
- The artifact store is local and supports atomic rename/move operations.
- A stable pipeline version identifier exists and is included in manifests.
