# DrySolidTdd Agent Constitution
<!-- Spec-Kit Constitution for a Coding Agent -->

## Core Principles

### I. DRY (Dont Repeat Yourself)
Single Source of Truth is mandatory.
- No duplicated logic, schemas, validations, or business rules.
- Common behavior must be extracted into shared modules or abstractions.
- Copy/paste is considered a defect unless explicitly justified.
- If the same idea appears twice, refactor.
- Configuration over duplication. Composition over repetition.

### II. SOLID Architecture
All design must conform to SOLID:

- Single Responsibility: Every module, class, and function has exactly one reason to change.
- Open/Closed: Extend behavior via composition or interfaces, not modification.
- Liskov Substitution: Subtypes must be drop-in replacements without surprises.
- Interface Segregation: Prefer small, focused interfaces over fat contracts.
- Dependency Inversion: Depend on abstractions, never concretions.

Practical enforcement:
- Explicit boundaries between domain, application, and infrastructure.
- No framework leakage into core logic.
- All external systems behind adapters.
- Constructors receive dependencies, never create them.

### III. Test-Driven Development (NON-NEGOTIABLE)
Strict Red-Green-Refactor.

Process:
1. Write tests first.
2. Assert observable behavior, not implementation.
3. Confirm tests fail.
4. Implement the minimal code to pass.
5. Refactor while keeping tests green.

Rules:
- No production code without a failing test.
- Every bug requires a regression test.
- Unit tests are mandatory for all domain logic.
- Test names must describe behavior, not mechanics.
- All Tests must pass after each specification is implmented.

### IV. Refactoring as a First-Class Activity
Refactoring is continuous, not optional.

- After green, always evaluate for DRY and SOLID violations.
- Reduce cyclomatic complexity.
- Eliminate speculative abstractions.
- Prefer clarity over cleverness.
- If design feels strained, refactor immediately.

### V. Simplicity and Determinism
- YAGNI (You Arent Gonna Need It).
- Smallest possible implementation that satisfies tests.
- Favor explicitness over magic.
- Deterministic behavior only, no hidden side effects.
- Pure functions preferred where feasible.

## Quality Gates

Code is considered shippable only if:

- All tests pass (unit + integration).
- Coverage exists for all business rules.
- No duplicated logic detected.
- SOLID violations addressed or explicitly justified.
- Public APIs documented.
- Static analysis produces zero high-severity findings.

Failing any gate blocks progress.

## Development Workflow

1. Clarify requirements as executable tests.
2. Implement via TDD loop.
3. Refactor for DRY and SOLID.
4. Add integration tests at system boundaries.
5. Run full test suite.
6. Perform architectural self-review.
7. Only then proceed to next task.

Additional rules:
- Features are developed vertically (tests → domain → adapters).
- No large batch commits.
- Each change must be independently testable.
- Incomplete work stays on branches.

## Governance

- This constitution supersedes convenience, speed, and personal preference.
- All changes must comply unless an explicit, documented exception is approved.
- Exceptions require:
  - Written justification
  - Defined scope
  - Follow-up refactor task

The agent must continuously audit its own output for:
- Duplication
- Responsibility creep
- Missing tests
- Overengineering

Violations must be corrected immediately.

**Version**: 1.0.0 | **Ratified**: 2026-02-05 | **Last Amended**: 2026-02-05
