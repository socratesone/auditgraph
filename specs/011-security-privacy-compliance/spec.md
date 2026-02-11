# Feature Specification: Security, Privacy, and Compliance Policies

**Feature Branch**: `011-security-privacy-compliance`  
**Created**: 2026-02-06  
**Status**: Draft  
**Input**: User description: "Define security, privacy, and compliance policies for storage handling, secret redaction, profile isolation, and export sharing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prevent secrets leakage (Priority: P1)

As a user ingesting notes, logs, and code into Auditgraph, I want derived artifacts and exports to avoid containing secrets so I can safely run automation and share outputs.

**Why this priority**: A single accidental secret leak into artifacts or exports undermines trust and can cause real-world incidents.

**Independent Test**: Can be fully tested by ingesting a fixture file containing known secret-like strings and verifying that derived artifacts and exports do not contain those strings, while still preserving enough structure to be useful.

**Acceptance Scenarios**:

1. **Given** a workspace with an ingested file containing a secret-like token, **When** the pipeline writes derived artifacts, **Then** the derived artifacts MUST not contain the original secret substring.
2. **Given** an export created from a profile, **When** the export is produced with default settings, **Then** any detected secret-like substrings MUST be redacted and the export MUST include redaction metadata.

---

### User Story 2 - Keep profiles isolated (Priority: P2)

As a user with multiple profiles (e.g., personal vs work), I want profile data and queries to be isolated so that running commands in one profile cannot read or export artifacts from another profile.

**Why this priority**: Profile mixing is a common, high-severity privacy failure mode and is difficult to detect after the fact.

**Independent Test**: Can be fully tested by creating two profiles with distinct artifacts and verifying that queries and exports only see the active profile unless an explicit cross-profile mode is used.

**Acceptance Scenarios**:

1. **Given** profile A and profile B each have artifacts, **When** a user runs a query under profile A, **Then** results MUST be computed solely from profile A storage.
2. **Given** profile A is active, **When** a user attempts to export from profile B without explicitly switching profiles, **Then** the command MUST refuse or export only from profile A.

---

### User Story 3 - Share clean-room exports (Priority: P3)

As a user who wants to share a graph snapshot with others, I want exports to be "clean-room" by default (redacted and metadata-labeled) so recipients can use them without gaining access to sensitive content.

**Why this priority**: Sharing is a primary workflow, and exports are the highest-likelihood leakage surface.

**Independent Test**: Can be fully tested by exporting a graph and verifying required metadata is present, and that no secret-like substrings appear in the exported payload.

**Acceptance Scenarios**:

1. **Given** an export is created, **When** it is produced with default settings, **Then** it MUST be redacted and labeled as safe-to-share.
2. **Given** an export is redacted, **When** a consumer inspects it, **Then** the export MUST contain enough metadata to understand what redaction policy was applied.

### Edge Cases

- Secret-like substrings appear multiple times across different sources.
- Secret-like substrings appear inside paths, identifiers, or frontmatter fields.
- A redaction match overlaps another match.
- A profile contains only partial artifacts (e.g., ingest exists but extract did not run).
- Exports are written to a user-specified output path outside the workspace.

### Test Plan

- **TP-001 (Profile isolation)**: Create two profiles with distinct entities and verify that queries run under profile A do not return entities that exist only in profile B.
- **TP-002 (Profile export boundary)**: Under profile A, create an export and verify it contains only artifacts from profile A.
- **TP-003 (Redaction in derived artifacts)**: Ingest a fixture containing secret-like strings and verify that the stored derived artifacts and indexes do not contain the original secret substrings.
- **TP-004 (Redaction in exports)**: Export the graph with defaults and verify the export contains redaction markers and does not contain original secret substrings.
- **TP-005 (Export metadata)**: Verify every export includes the required metadata fields and redaction summary counts.

## Requirements *(mandatory)*

### Functional Requirements

#### Data Classification and Storage Handling

- **FR-001**: The system MUST classify data into at least four handling classes: **Public**, **Internal**, **Sensitive**, and **Secret**.
- **FR-002**: The system MUST treat any detected credentials, authentication tokens, private keys, or password-equivalent values as **Secret**.
- **FR-003**: The system MUST ensure that **Secret** values do not appear in derived artifacts (entities, claims, links, indexes, manifests, or exports) produced from ingested content.
- **FR-004**: The system MUST store all derived artifacts under the active profile’s package root: `.pkg/profiles/<profile>/...`.
- **FR-005**: The system MUST NOT read from or write to any other profile’s `.pkg/profiles/<other-profile>/...` directory when operating in a single active profile.

#### Encryption at Rest (Decision and Scope)

- **FR-006**: Encryption at rest is an environmental requirement: users who require encryption at rest MUST place the workspace and `.pkg/` directory on encrypted storage.
- **FR-007**: Because encryption is environmental, the system MUST default to minimizing the sensitivity of what it persists by enforcing redaction rules for **Secret** values in all derived artifacts and exports.

#### Secrets Detection and Redaction Policy

- **FR-008**: The system MUST implement pattern-based detection for secret-like content in text fields that can propagate into derived artifacts and exports (including titles, extracted text snippets, identifiers, and metadata fields).
- **FR-009**: At minimum, the detection set MUST cover these categories:
  - Private keys (e.g., PEM-like blocks)
  - Common access-token formats (long high-entropy strings with known prefixes)
  - Password assignments (e.g., `password=...`, `pwd: ...`, `token: ...`)
  - Cloud-provider access key identifiers (format-based)
- **FR-010**: When a match is detected, the system MUST replace the matched substring with a stable redaction marker that preserves readability without exposing the original value (for example: `[REDACTED:SECRET]`).
- **FR-011**: Redaction MUST be deterministic: for the same input text and policy version, the same output MUST be produced.
- **FR-012**: Redaction MUST be loss-aware: the system MUST record a redaction event in metadata (counts by category at minimum) for each export and for each run manifest that references redaction.

**Examples (behavioral)**:

- Input: `password=CorrectHorseBatteryStaple` → Output MUST contain `password=[REDACTED:SECRET]`
- Input contains a private key block → Output MUST contain `[REDACTED:SECRET]` in place of the key material

#### Profile Isolation and Query Boundaries

- **FR-013**: Profile isolation MUST be enforced by file-path boundaries:
  - Reads and writes for artifacts MUST be confined to `.pkg/profiles/<active-profile>/...`.
  - Source discovery MUST be limited to the include/exclude rules of the active profile.
- **FR-014**: Query operations MUST only read indexes and artifacts under the active profile package root.
- **FR-015**: Export operations MUST only read entities/links/claims/indexes from the active profile package root.
- **FR-016**: Any cross-profile behavior (if ever supported) MUST require explicit user intent and MUST produce outputs that clearly label all included profiles.

#### Export Policy (Redaction + Clean-Room Sharing)

- **FR-017**: Exports MUST be redacted by default.
- **FR-018**: Exports MUST include an export metadata section that contains at minimum:
  - Export creation time
  - Active profile name
  - Workspace-relative root identifier (non-sensitive)
  - Redaction policy version identifier
  - Redaction summary counts by category
  - A flag indicating the export is intended for clean-room sharing
- **FR-019**: If an export is produced with redaction disabled (if such a mode exists), the system MUST clearly label the export as **NOT SAFE TO SHARE** and MUST require an explicit user opt-in.
- **FR-020**: Export paths MUST NOT allow path traversal to escape intended output locations when given a workspace-relative path.

#### Assumptions and Dependencies

- **A-001**: Users who require encryption at rest will place the workspace and `.pkg/` directory on encrypted storage.
- **A-002**: Redaction is applied to derived artifacts and exports; original source files are treated as user-controlled inputs and are not rewritten by default.
- **D-001**: Profile isolation depends on all pipeline, query, and export paths being derived from the active profile package root.

#### Out of Scope

- Implementing a proprietary encryption-at-rest mechanism within the tool.
- Modifying user-owned source files as part of redaction.
- Cross-profile querying or exporting without explicit user intent.

### Key Entities *(include if feature involves data)*

- **Profile**: A named configuration context that scopes what sources are ingested and where artifacts are stored.
- **Data Classification**: A policy label (Public/Internal/Sensitive/Secret) that determines storage and sharing handling.
- **Redaction Policy**: A versioned set of deterministic rules that identifies and replaces secret-like substrings.
- **Redaction Event Summary**: Aggregate metadata describing redactions applied (counts and categories).
- **Export Metadata**: A machine-readable description bundled with exports that declares profile, policy version, and safety labeling.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In automated tests, 100% of derived artifacts and exports produced from fixtures containing secret-like strings contain zero occurrences of the original secret substrings.
- **SC-002**: For two profiles with different artifacts, 100% of query and export operations run under one profile return results only from that profile unless explicit cross-profile mode is enabled.
- **SC-003**: 100% of exports produced with defaults include export metadata with redaction summary and a clean-room sharing flag.
- **SC-004**: Users can generate a redacted export and confirm it is safe-to-share in under 2 minutes using the documented workflow.
