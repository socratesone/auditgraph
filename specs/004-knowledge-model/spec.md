# Feature Specification: Knowledge Model

**Feature Branch**: `specification-updates`
**Status**: Approved

## Overview
Auditgraph stores a deterministic knowledge model of entities and claims with explicit provenance.
Entity types are namespaced and claims can include optional validity windows and contradiction flags.

## Entity Schema
Required fields:
- `id`, `type`, `name`, `canonical_key`, `provenance`

Optional fields:
- `aliases` (list), `refs` (list)

### Entity Types (day 1)
- `ag:note`, `ag:task`, `ag:decision`, `ag:event`, `ag:entity`

## Claim Schema
Required fields:
- `id`, `subject_id`, `predicate`, `object`, `provenance`

Optional fields:
- `confidence`, `validity_window`, `contradiction`, `contradiction_reason`

## Canonical Keys and Namespacing
- Canonical keys MUST be lowercase with spaces replaced by `_`.
- Entity types MUST be namespaced with `ag:` by default.
- Secondary namespaces are allowed but normalized to `ag:` when disallowed by config.

## Contradictions
- Conflicting claims MUST be retained and flagged with `contradiction: true`.
- `contradiction_reason` MUST be a human-readable string.

## Temporal Validity
- Claims MAY include `validity_window` with `start` and `end`.
- Missing validity windows are treated as timeless facts.

## Confidence
- Confidence MUST be rule-based for day 1.
- Model-derived confidence is out of scope.

## Acceptance Tests
- Entity and claim validation returns no missing fields for valid payloads.
- Namespace resolution converts `note` to `ag:note`.
- Contradiction flagging sets `contradiction` and `contradiction_reason`.
- Canonical key generation normalizes "My Note" -> `my_note`.

## Success Criteria
- 100% of stored claims include required fields.
- Namespacing is deterministic for all entities.
