# Quickstart: Linking and Explainability

## Goal

Use this spec to understand link generation policy, explainability payloads, and backlinks strategy.

## Steps

1. Review [specs/007-linking-explainability/spec.md](specs/007-linking-explainability/spec.md) for link policy and requirements.
2. Read [specs/007-linking-explainability/data-model.md](specs/007-linking-explainability/data-model.md) for link entities and validation rules.
3. Use [specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml](specs/007-linking-explainability/contracts/linking-explainability.openapi.yaml) to align payload fields with API consumers.
4. Confirm deterministic ordering and backlinks policy in the spec.

## Success Check

- Links include rule id and evidence references.
- Backlink policy is documented and deterministic.
