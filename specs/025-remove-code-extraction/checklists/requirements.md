# Specification Quality Checklist: Remove Code Extraction, Narrow Scope to Documents & Provenance

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- All items pass validation.
- Requirements reference specific file paths (`auditgraph/extract/code_symbols.py`, `auditgraph/ingest/policy.py`, etc.) because this is a scope-narrowing / deletion spec where the files to be removed are the subject of the specification itself. These references describe *what* is being removed, not *how*, and are necessary for unambiguous acceptance testing.
- Four user stories covering: (US1) git provenance produces file entities for all file types, (US2) documented feature set matches actual behavior, (US3) dead code and dead config removed, (US4) existing workspaces remain queryable after upgrade.
- Two P1 user stories (US1, US2) are the load-bearing pieces; US3 and US4 are P2 follow-ons. US1 (file entity migration) is a strict prerequisite for US3 (deletion) — removing `extract_code_symbols` without first fixing file entity creation in git provenance would expand the pre-existing dangling-reference bug rather than fix it.
- The Clarifications section pre-resolves six questions that would otherwise have been `[NEEDS CLARIFICATION]` markers, using verification findings from the preceding design conversation.
- Success criteria SC-005 and SC-006 use grep-based verification as an objective test — "the string `code_symbols` does not appear in runtime code" is a concrete binary pass/fail.
- This spec explicitly closes the scope-on-code open question from `specs/024-document-classification-and-model-selection/NOTES.md` (that question was flagged as blocking before spec 024 could proceed). This spec's acceptance implies that spec 024 § 4 is dead and will be replaced with a tombstone per FR-026.
