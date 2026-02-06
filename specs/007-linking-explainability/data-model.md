# Data Model: Linking and Explainability

## Entities

### Link Rule
- Fields: rule_id, rule_type (deterministic | suggestion), match_strategy, link_type, confidence
- Relationships: produces Link Artifacts

### Link Artifact
- Fields: version, id, from_id, to_id, type, rule_id, confidence, evidence[], explanation{}
- Relationships: referenced by graph indexes and explainability output

### Explainability Payload
- Fields: rule_id, evidence, score, matched_terms?
- Relationships: attached to Link Artifact

### Backlink Policy
- Fields: strategy (on_demand | stored), storage_path?, refresh_policy?
- Relationships: applies to link traversal

## Validation Rules
- Link artifacts include rule_id and evidence references.
- Suggested links are marked non-authoritative.
- Explainability payload includes rule_id and evidence.
- Link ordering is deterministic (type, rule_id, from_id, to_id).

## State Transitions
- Links are immutable once written; updated rules create new link artifacts.
