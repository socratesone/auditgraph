# Feature Specification: Linking and Explainability

**Feature Branch**: `007-linking-explainability`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Define linking rules, explainability payloads, and backlinks policy"

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

### User Story 1 - Deterministic Link Rules (Priority: P1)

As a maintainer, I want deterministic link rules so that authoritative links are reproducible and auditable.

**Why this priority**: Deterministic linking is required for trust and reproducibility.

**Independent Test**: Review the spec to verify link generation policy, supported link types, and required metadata for authoritative links.

**Acceptance Scenarios**:

1. **Given** two artifacts that match a rule, **When** I apply the link rules, **Then** the same link is produced every time with the same metadata.
2. **Given** a rule is configured as deterministic, **When** links are generated, **Then** the output is marked authoritative and reproducible.

---

### User Story 2 - Explainability Payloads (Priority: P2)

As a reviewer, I want explainability payloads so I can see the rule and evidence behind each link.

**Why this priority**: Explainability is necessary to trust and validate the graph.

**Independent Test**: Verify that each link payload includes the rule id, evidence snippet, and scores where applicable.

**Acceptance Scenarios**:

1. **Given** a link, **When** I inspect its explanation, **Then** I can identify the rule and evidence used to create it.

---

### User Story 3 - Backlinks Policy (Priority: P3)

As an operator, I want a clear backlinks policy so that neighborhood traversal remains deterministic and performant.

**Why this priority**: Backlink policy affects storage, performance, and determinism.

**Independent Test**: Confirm the spec states whether backlinks are computed on demand or stored, and under what conditions.

**Acceptance Scenarios**:

1. **Given** a node, **When** I request backlinks, **Then** the response follows the documented policy (on-demand by default).

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Conflicting rules produce multiple link candidates for the same pair.
- Evidence snippet cannot be resolved because the source moved or changed.
- Similarity-based suggestions are generated but must be marked non-authoritative.
- Backlinks requested when link artifacts are missing.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The specification MUST define the link generation policy, including authoritative deterministic links and optional suggestions.
- **FR-002**: The specification MUST list supported link types and required metadata for each type.
- **FR-003**: Each link artifact MUST include a rule identifier and evidence references.
- **FR-004**: Explainability payloads MUST include rule id, evidence snippet reference, and scores when applicable.
- **FR-005**: Suggested (non-authoritative) links MUST be explicitly marked as such.
- **FR-006**: The specification MUST define the backlinks policy, including default computation strategy.
- **FR-007**: The specification MUST define how link conflicts are handled and surfaced.
- **FR-008**: The specification MUST define stable ordering for link outputs to preserve determinism.

## Link Policy Summary

- Deterministic rules produce authoritative links.
- Optional suggestion rules are allowed but must be marked non-authoritative.
- Supported link types: mentions, defines, implements, depends_on, decided_in, relates_to, cites.

## Explainability Summary

- Explainability payload includes rule id, evidence references, and scores when applicable.
- Evidence references point to source artifacts, not duplicated text.

## Backlinks Summary

- Backlinks are computed on demand in MVP.
- Stored backlinks are allowed only for performance reasons.
- Ordering is deterministic: type, rule_id, from_id, to_id.

### Key Entities *(include if feature involves data)*

- **Link Rule**: Deterministic or suggestion rule that produces a link candidate.
- **Link Artifact**: Directed edge with type, rule id, evidence, and confidence.
- **Explainability Payload**: Structured reason for link creation (rule, evidence, score).
- **Backlink Policy**: Definition of how inverse links are computed or stored.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of link types have documented required metadata and rule identifiers.
- **SC-002**: 100% of links include an explainability payload with rule and evidence references.
- **SC-003**: Backlink policy is documented and applicable to all link types.
- **SC-004**: Two reviewers can independently apply the link policy and reach the same interpretation.

## Assumptions

- Deterministic rules produce authoritative links; suggestions are optional and clearly flagged.
- Backlinks are computed on demand in MVP and stored only when performance requires it.
