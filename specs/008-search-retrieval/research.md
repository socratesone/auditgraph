# Research: Search and Retrieval

## Decision 1: Query Types

- **Decision**: Support keyword, hybrid (keyword + semantic), graph traversal, and show sources for claim.
- **Rationale**: Aligns with core workflows and clarifying answers.
- **Alternatives considered**: Keyword-only. Rejected because traversal and provenance queries are required.

## Decision 2: Ranking and Tie-breaks

- **Decision**: Deterministic scoring with tie-break order: score, stable_id, normalized path.
- **Rationale**: Ensures stable ordering across runs and platforms.
- **Alternatives considered**: Unordered results. Rejected due to determinism requirements.

## Decision 3: Explanation Payload

- **Decision**: Explanation includes matched terms, rule id when applicable, and evidence references.
- **Rationale**: Provides auditability without duplicating source content.
- **Alternatives considered**: Only score. Rejected because evidence is required for trust.

## Decision 4: Offline-first and Embeddings

- **Decision**: Core search is offline; semantic search is optional and CPU-only with model size <= 1.5 GB.
- **Rationale**: Maintains offline-first policy while allowing optional semantic capability.
- **Alternatives considered**: Required semantic search. Rejected due to resource constraints.
