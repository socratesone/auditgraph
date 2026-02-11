# Implementation Plan: Security, Privacy, and Compliance Policies

**Branch**: `011-security-privacy-compliance` | **Date**: 2026-02-06 | **Spec**: [specs/011-security-privacy-compliance/spec.md](spec.md)
**Input**: Feature specification from `/specs/011-security-privacy-compliance/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement deterministic safety controls so Auditgraph can ingest, index, query, and export without leaking secret material and without mixing data across profiles.

Planned scope:
- Deterministic secret detection + redaction applied before persistence/indexing/export.
- Hard profile isolation via `.pkg/profiles/<active-profile>/...` boundaries.
- Export clean-room defaults: redacted-by-default plus required export metadata.
- Path safety for user- and config-supplied output paths.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >=3.10  
**Primary Dependencies**: stdlib, `pyyaml` (config), `pytest` (tests)  
**Storage**: Filesystem artifacts under `.pkg/profiles/<profile>/...` and `exports/...`  
**Testing**: pytest (unit + integration)  
**Target Platform**: Local CLI (Linux/macOS/Windows considerations; current dev on Linux)
**Project Type**: Single Python package (`auditgraph/`)  
**Performance Goals**: Redaction must be linear in text size for typical files; no global O(n^2) scans.  
**Constraints**: Deterministic outputs; avoid leaking secrets into any derived artifacts; minimal UX surface area changes.  
**Scale/Scope**: Typical local workspaces (10s–1000s files per run; derived artifacts per profile).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **DRY**: Centralize redaction + path boundary enforcement in shared utilities (no copy/paste regexes across pipeline/export/jobs).
- **SOLID**: Separate concerns: detection ruleset, redaction transform, path-policy enforcement, and export metadata composition.
- **TDD (non-negotiable)**: Add failing tests first for redaction, profile isolation, and path traversal safety; then implement minimal code.
- **Determinism**: Redaction markers and metadata must be stable for the same input + policy version; avoid random IDs.

GATE STATUS: PASS (planning only; implementation will be blocked until tests exist and pass).

## Project Structure

### Documentation (this feature)

```text
specs/011-security-privacy-compliance/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
auditgraph/
├── cli.py
├── config.py
├── export/
├── ingest/
├── jobs/
├── pipeline/
├── query/
├── storage/
└── utils/

config/
├── pkg.yaml
├── jobs.yaml
└── profiles/

tests/
├── test_cli_integration.py
├── test_smoke.py
└── test_spec011_*.py  # to be added for this feature
```

**Structure Decision**: Single Python package with pytest tests under `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
