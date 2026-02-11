# Feature Specification: Distribution, Packaging, and Upgrades

**Feature Branch**: `012-distribution-packaging-upgrades`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "see 12-distribution-packaging-upgrades.md for details. spec/branch number 012."

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

### User Story 1 - Install and run on supported OS (Priority: P1)

As an engineer, I can install Auditgraph on a supported OS and run the CLI without manual code edits.

**Why this priority**: Distribution is the entry point; if install and execution are unreliable, no other features are usable.

**Independent Test**: Can be fully tested by installing on each supported OS target and running `auditgraph version`.

**Acceptance Scenarios**:

1. **Given** a supported OS with Python available, **When** I install the package and run `auditgraph version`, **Then** it returns a version string.
2. **Given** an unsupported OS, **When** I attempt to install or run the package, **Then** the tooling documents that OS is unsupported and does not claim compatibility.

---

### User Story 2 - Upgrade without data loss (Priority: P2)

As an engineer, I can upgrade Auditgraph and keep existing workspaces safe, with clear guidance on rebuilds when formats change.

**Why this priority**: Users need confidence that upgrades are safe and do not corrupt prior artifacts.

**Independent Test**: Can be fully tested by creating a workspace on one version, upgrading, and confirming upgrade behavior according to the compatibility rules.

**Acceptance Scenarios**:

1. **Given** a workspace created on a compatible version, **When** I run `auditgraph ingest`, **Then** it completes without migration warnings.
2. **Given** a workspace created on an incompatible artifact schema version, **When** I run `auditgraph ingest`, **Then** the tool detects the mismatch and instructs me to rebuild in a new run without modifying existing artifacts.

---

### User Story 3 - Enforce disk footprint budgets (Priority: P3)

As an engineer, I can control how much disk space derived artifacts and indexes consume, and the tool enforces that limit predictably.

**Why this priority**: Storage growth is a common operational risk; clear limits keep workspaces manageable.

**Independent Test**: Can be fully tested by configuring a small budget and verifying that the tool blocks or warns when thresholds are exceeded.

**Acceptance Scenarios**:

1. **Given** a configured disk budget, **When** a new run would exceed the limit, **Then** the tool stops before writing new artifacts and reports the overage.
2. **Given** usage below the warning threshold, **When** I run ingest or export, **Then** no budget warning is emitted.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- When the workspace has zero source files, budget calculations treat source size as a minimum of 1 MB to avoid division by zero.
- When a prior run is missing manifests or schema version fields, the tool treats it as incompatible and requires a rebuild.
- When the export destination is on a different filesystem, the disk budget check still applies to the workspace artifacts directory.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST support day-1 operation on Linux and macOS; Windows is explicitly out of scope for day 1.
- **FR-002**: System MUST publish a Python package that installs a console entrypoint named `auditgraph`.
- **FR-003**: System MUST document the installation steps for supported OS targets using the published package.
- **FR-004**: System MUST record an artifact schema version in each run manifest and derived artifact manifest.
- **FR-005**: System MUST allow upgrades that keep existing artifacts readable when schema versions are compatible.
- **FR-006**: System MUST treat incompatible artifact schema versions as requiring a rebuild and MUST NOT rewrite or delete existing artifacts.
- **FR-007**: System MUST provide a deterministic rebuild path that writes new artifacts under a new run identifier.
- **FR-008**: System MUST enforce disk footprint budgets for derived artifacts and indexes relative to the size of ingested sources.
- **FR-009**: System MUST warn at 80% of the configured budget and MUST stop writing new derived artifacts at 100% of the budget.
- **FR-010**: System MUST report the current budget usage and thresholds in command output when a warning or block occurs.

### Supported OS Targets

- Linux (x86_64) and macOS (Intel and Apple Silicon) are supported for day 1.
- Windows is not supported for day 1; documentation MUST state this clearly.

### Packaging and Installation

- Installation uses `pip install auditgraph` from a Python package index.
- The package MUST expose a console entrypoint named `auditgraph`.
- The package MUST declare a minimum supported Python version of 3.10.

### Upgrade and Migration Rules

- If artifact schema versions are compatible, the tool proceeds without migration warnings.
- If versions are incompatible, the tool MUST refuse to reuse old derived artifacts and instruct the user to rebuild.
- Rebuilds MUST be non-destructive and MUST preserve prior runs.

### Disk Footprint Budgets

- Default budget for derived artifacts and indexes is 3x the total size of ingested source files.
- Budget checks apply to the workspace derived-artifact directory (the per-profile `.pkg` area).
- Users MUST be able to override the budget through configuration.

### Verification Plan

- Verify installation on Linux and macOS by installing the package and running `auditgraph version`.
- Create a workspace, generate artifacts, upgrade the package, and confirm compatibility behavior.
- Configure a low disk budget, run ingest, and verify warning and blocking behavior.

### Key Entities *(include if feature involves data)*

- **ArtifactSchemaVersion**: A recorded version identifier in run and artifact manifests used for compatibility checks.
- **FootprintBudget**: A configured limit defined as a multiplier of source size, including warning and block thresholds.

### Assumptions

- Supported OS targets are limited to Linux and macOS for day 1, based on current non-functional requirements.
- Users can access a Python package index to install the CLI.
- Derived artifact storage remains under the workspace `.pkg` directory and is rebuildable.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 95% of install attempts on supported OS targets complete successfully within 5 minutes.
- **SC-002**: 100% of upgrade tests with compatible schema versions complete without rebuild prompts.
- **SC-003**: 100% of tests with incompatible schema versions trigger a rebuild instruction and preserve previous artifacts.
- **SC-004**: Budget warnings trigger at 80% usage and blocks at 100% in 100% of automated tests.
