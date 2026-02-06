# Linking Rules & Explainability

## Purpose
Define deterministic link rules, optional similarity rules, evidence payloads, and backlink strategy.

## Source material
- [SPEC.md](SPEC.md) Linking and Navigation
- [SPEC.md](SPEC.md) Search explainability

## Decisions Required
- Link generation policy (strict deterministic vs optional suggestions).
- Supported link types and required metadata.
- Explainability payload requirements (rule, evidence snippet, scores).
- Backlinks policy (stored vs computed on demand).

## Decisions (filled)

### Link Generation Policy

- Deterministic rules produce authoritative links.
- Optional suggestion rules are allowed but must be marked non-authoritative.

### Link Types

Supported types: mentions, defines, implements, depends_on, decided_in, relates_to, cites.

Required metadata for all link types:
- `rule_id`
- `confidence`
- `evidence` (source pointer(s))
- `authority` (authoritative | suggested)

### Explainability Payload

Explainability must include:
- `rule_id`
- `evidence` reference(s)
- `score` when applicable
- `matched_terms` when applicable

### Backlinks Policy

- Backlinks are computed on demand in MVP.
- Backlinks may be stored when performance requires it.
- Ordering is deterministic: type, rule_id, from_id, to_id.

## Resolved

- Deterministic rules are authoritative; suggestions are explicitly flagged.
- Supported link types and required metadata are defined.
- Explainability payload includes rule id, evidence, and scores where applicable.
- Backlinks computed on demand with deterministic ordering.
