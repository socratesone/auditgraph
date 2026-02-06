# Data Model: Search and Retrieval

## Entities

### Query
- Fields: query_id, type, text, filters, issued_at
- Relationships: produces Result entries

### Result
- Fields: id, type, score, explanation
- Relationships: references source artifacts and links

### Explanation
- Fields: matched_terms, rule_id?, evidence[], tie_break[]
- Relationships: attached to Result

### Ranking Policy
- Fields: score_weights, tie_break_order, rounding
- Relationships: applied to query results

## Validation Rules
- Results include id, type, score, and explanation.
- Explanation includes matched terms and evidence references.
- Tie-break keys are always populated for stable ordering.

## State Transitions
- Query results are immutable once returned; new runs produce new result sets.
