# Data Model

## Entities

### Entity
- Fields: id, type, name, canonical_key, aliases, provenance, refs

### Claim
- Fields: id, subject_id, predicate, object, provenance, confidence, validity_window?

### Note
- Fields: id, title, body, tags, project, status, provenance

### Task
- Fields: id, title, status, due_date?, provenance

### Decision
- Fields: id, title, rationale, consequences, provenance

### Event
- Fields: id, title, time_start, time_end?, participants?, provenance

## Validation Rules
- Claims must include subject, predicate, and object.
- Contradictions are flagged and stored separately (no deletion).
- Confidence is rule-based and stored with provenance.
- Namespaces are applied to type identifiers.

## State Transitions
- Claims can transition from proposed → accepted/rejected.
- Timeless claims have no validity window.
