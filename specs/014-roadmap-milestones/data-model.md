# Data Model: Roadmap and Milestones

**Branch**: 014-roadmap-milestones  
**Date**: 2026-02-11  
**Spec**: [specs/014-roadmap-milestones/spec.md](spec.md)

This feature defines the data concepts used in the roadmap documentation.

## Entities

### Phase
Represents a milestone phase in the roadmap.

**Fields**
- `phase_id` (string): 0 through 6
- `name` (string): Phase name
- `deliverables` (list[string]): Concrete commands or artifacts
- `exit_criteria` (list[string]): Measurable validation steps
- `dependencies` (list[string]): Prior phase IDs

**Rules**
- Every phase must list deliverables and exit criteria.
- Dependencies must reference earlier phases only.

---

### Deliverable
Represents a concrete output of a phase.

**Fields**
- `label` (string): Human-readable description
- `validation` (string): How to validate the deliverable

---

### ExitCriteria
Represents a measurable completion check for a phase.

**Fields**
- `metric` (string): The validation metric or command
- `expected` (string): Expected outcome
