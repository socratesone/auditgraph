# Feature Specification: Storage Layout and Artifacts

**Feature Branch**: `006-storage-layout-artifacts`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Finalize storage layout, artifact schemas, sharding rules, and stable ID canonicalization"

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

### User Story 1 - Directory Layout (Priority: P1)

As a maintainer, I want a consistent directory layout so that artifacts are predictable, inspectable, and easy to diff.

**Why this priority**: Storage layout is foundational for determinism and operational support.

**Independent Test**: Review the spec and confirm that each artifact type has a defined path and naming convention.

**Acceptance Scenarios**:

1. **Given** an artifact type (source, entity, claim, link, index), **When** I look up the layout, **Then** I find its canonical storage path and naming rule.
2. **Given** a run identifier and profile, **When** I navigate the layout, **Then** I can locate all artifacts for that run.

---

### User Story 2 - Artifact Schemas (Priority: P2)

As a reviewer, I want artifact schemas defined so that auditing, diffing, and downstream tooling can rely on stable fields.

**Why this priority**: Schemas ensure consistent interpretation of artifacts across runs and tools.

**Independent Test**: Validate that each artifact schema lists required fields and versioning rules.

**Acceptance Scenarios**:

1. **Given** an artifact schema, **When** I read it, **Then** I can identify required fields and their meanings.

---

### User Story 3 - Sharding and Stable IDs (Priority: P3)

As an operator, I want sharding and stable ID rules documented so that large stores remain performant and deterministic.

**Why this priority**: Sharding and stable IDs protect scalability and determinism over time.

**Independent Test**: Confirm that the spec defines shard rules and canonicalization steps for stable IDs.

**Acceptance Scenarios**:

1. **Given** a canonical key, **When** I follow the stable ID rules, **Then** the resulting ID and shard path are deterministic.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Artifact path conflicts between profiles.
- Shard directory missing or partially written.
- Schema version mismatch between runs.
- Canonicalization rules change between versions.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The specification MUST define the canonical directory layout for artifacts under `.pkg/profiles/<profile>/`.
- **FR-002**: The specification MUST define naming conventions for run folders and per-artifact files.
- **FR-003**: The specification MUST define schemas for sources, entities, claims, links, and indexes with required fields.
- **FR-004**: Each artifact schema MUST include a version identifier and compatibility rule.
- **FR-005**: The specification MUST define sharding rules, including prefix length and shard placement for artifact IDs.
- **FR-006**: The specification MUST define stable ID canonicalization inputs and hashing rules for entities, claims, and links.
- **FR-007**: The specification MUST define how schema or canonicalization changes are versioned.
- **FR-008**: The specification MUST define how index artifacts reference their input manifests.

## Directory Layout Summary

Artifacts are stored under `.pkg/profiles/<profile>/` with run manifests under `runs/<run_id>/`. Canonical paths are documented in [docs/spec/06-storage-layout-artifacts.md](docs/spec/06-storage-layout-artifacts.md).

## Stable ID Canonicalization Summary

- Canonical inputs are normalized paths and stable text forms.
- IDs are derived by hashing canonical inputs with sha256 and type prefixes.
- Canonicalization and schema changes require version bumps.

### Key Entities *(include if feature involves data)*

- **Artifact Root**: Profile-scoped directory containing all derived outputs.
- **Source Artifact**: Parsed source metadata and hashes.
- **Entity Artifact**: Canonical node representation with provenance.
- **Claim Artifact**: Fact assertion with provenance and optional qualifiers.
- **Link Artifact**: Directed edge with evidence and rule id.
- **Index Artifact**: Search or graph index shards with manifest references.
- **Stable ID**: Deterministic identifier derived from canonical inputs.
- **Shard**: Directory partition based on ID prefix.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of artifact types have a documented canonical path and naming rule.
- **SC-002**: 100% of artifact schemas list required fields and a version identifier.
- **SC-003**: Stable ID and sharding rules can be applied consistently by two reviewers with no discrepancies.
- **SC-004**: Reviewers can locate any artifact for a given run in under 5 minutes using the spec.

## Assumptions

- The storage root is local and profile-scoped under `.pkg/profiles/<profile>/`.
- Sharding is based on deterministic ID prefixes.
- Schema versioning uses explicit version fields rather than inferred structure.
