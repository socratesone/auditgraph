# Feature Specification: Roadmap and Milestones

**Feature Branch**: `014-roadmap-milestones`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "See 14-roadmap-milestones.md for details. spec/branch number 014."

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

### User Story 1 - Track phased delivery (Priority: P1)

As a project owner, I can see a clear phase list with deliverables and measurable exit criteria.

**Why this priority**: The roadmap is the primary coordination artifact for phased delivery.

**Independent Test**: Can be fully tested by validating that each phase lists deliverables and exit criteria that are measurable.

**Acceptance Scenarios**:

1. **Given** the roadmap, **When** I review a phase, **Then** it lists concrete deliverables and exit criteria.
2. **Given** a phase exit, **When** I check the criteria, **Then** each criterion maps to a measurable validation step.

---

### User Story 2 - Enforce phase dependencies (Priority: P2)

As a project owner, I can see dependencies between phases so sequencing is explicit.

**Why this priority**: Dependencies prevent premature work that would invalidate later phases.

**Independent Test**: Can be fully tested by verifying that each phase lists explicit prerequisites.

**Acceptance Scenarios**:

1. **Given** the roadmap, **When** I review Phase 3, **Then** it lists dependencies on prior phases.
2. **Given** a dependency is unmet, **When** the phase is evaluated, **Then** the roadmap indicates it is blocked.

---

### User Story 3 - Validate roadmap completeness (Priority: P3)

As a stakeholder, I can confirm the roadmap covers all phases from scaffold to automation without ambiguous language.

**Why this priority**: Completeness ensures consistent planning and reduces scope drift.

**Independent Test**: Can be fully tested by checking that phases 0–6 are present with measurable exit criteria.

**Acceptance Scenarios**:

1. **Given** the roadmap, **When** I audit it, **Then** phases 0–6 are present with explicit deliverables.
2. **Given** any ambiguous timeline language, **When** it appears, **Then** the roadmap marks it as invalid.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- When a phase deliverable is partially complete, the phase is still considered incomplete until all exit criteria pass.
- When a phase depends on an optional feature, the dependency is still required if the optional feature is part of the phase deliverables.
- When a deliverable is renamed, exit criteria must be updated to match the new identifier.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The roadmap MUST define phases 0 through 6 with deliverables aligned to SPEC.md.
- **FR-002**: Each phase MUST list concrete deliverables (commands or artifacts).
- **FR-003**: Each phase MUST include measurable exit criteria with validation steps.
- **FR-004**: The roadmap MUST document dependencies between phases.
- **FR-005**: The roadmap MUST avoid ambiguous timeline language and focus on deliverables.

### Phase List With Deliverables

- **Phase 0: repo + scaffolding**: CLI skeleton, config loader, canonicalization utilities, run manifest structure; deliverable: `auditgraph init`, `auditgraph version`, `auditgraph config validate`.
- **Phase 1: ingestion + hashing**: directory scan, hashing, ingest manifest, Markdown/plain text parser; deliverable: `auditgraph ingest` produces `.pkg/sources` and run manifest.
- **Phase 2: deterministic extraction**: entity extraction from notes and code files, deterministic claim extraction, extractor plugins; deliverable: `auditgraph extract` creates entity/claim artifacts.
- **Phase 3: linking**: deterministic link rules with explainable evidence; deliverable: `auditgraph link` creates link artifacts and adjacency output.
- **Phase 4: hybrid search**: BM25 index, query explanation, optional embeddings behind feature flag; deliverable: `auditgraph query` returns JSON with explanations.
- **Phase 5: UI graph nav**: CLI node view, neighbors, why-connected, optional local UI; deliverable: navigation and search UX is usable on sample workspace.
- **Phase 6: automation + plugins**: job scheduler, review queue, plugin registry; deliverable: scheduled digests, stale-link checks, plugin SDK docs.

### Exit Criteria (Measurable)

- **Phase 0**: `auditgraph version` returns a semantic version and `auditgraph init` creates `.pkg` and `config/pkg.yaml`.
- **Phase 1**: `auditgraph ingest` produces a run manifest with records and writes source metadata artifacts.
- **Phase 2**: `auditgraph extract` produces entity and claim artifacts with provenance fields present.
- **Phase 3**: `auditgraph link` produces link artifacts with rule IDs and evidence references.
- **Phase 4**: `auditgraph query` returns results with explanations and deterministic ordering.
- **Phase 5**: CLI graph navigation commands return valid JSON payloads for node, neighbors, and why-connected.
- **Phase 6**: `auditgraph jobs run` produces stored outputs and plugin registry loads at least one example plugin.

### Dependencies

- Phase 0 blocks all subsequent phases.
- Phase 1 depends on Phase 0 completion.
- Phase 2 depends on Phase 1 completion.
- Phase 3 depends on Phase 2 completion.
- Phase 4 depends on Phase 3 completion.
- Phase 5 depends on Phase 4 completion.
- Phase 6 depends on Phase 5 completion.

### Key Entities *(include if feature involves data)*

- **Phase**: A milestone with deliverables and exit criteria.
- **Deliverable**: A concrete command or artifact produced by a phase.
- **ExitCriteria**: Measurable checks that must pass to complete a phase.

### Assumptions

- Phase definitions and deliverables align with SPEC.md milestones.
- Roadmap is documentation-only and does not imply runtime behavior.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of phases list deliverables and exit criteria.
- **SC-002**: 100% of exit criteria are measurable and map to validation steps.
- **SC-003**: All phase dependencies are explicit and ordered 0 through 6.
- **SC-004**: Roadmap contains no ambiguous timeline language (no dates or subjective terms).
