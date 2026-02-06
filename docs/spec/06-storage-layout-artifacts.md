# Spec Blueprint: Storage Layout and Artifacts

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable storage layout and artifact schema spec covering directories,
sharding, and stable identifiers.

## Source material
- [SPEC.md](SPEC.md) Storage layout, Stable IDs, Example artifacts

## Required decisions the spec must make
- Directory layout and naming conventions under `.pkg/profiles/<profile>/`.
- Artifact schemas and required fields for each artifact type.
- Sharding rules and shard placement logic.
- Stable ID canonicalization rules and versioning strategy.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Directory tree with exact paths for runs, sources, entities, claims, links, indexes, provenance.
2) Artifact schemas with required fields and version attributes.
3) Sharding rules with examples showing id -> shard mapping.
4) Stable ID canonicalization inputs and hashing rules.
5) Backward compatibility and version bump rules.
6) Test plan with at least:
	- artifact path placement
	- shard resolution correctness
	- schema validation for required fields

## Definition of done for the spec
- The spec defines exact file paths and JSON fields for every artifact.
- The spec includes examples that a reviewer can validate by inspection.
- The spec includes acceptance criteria and tests that map to code changes.

## Guardrails
- Do not describe runtime pipeline behavior here except as it affects storage.
- Avoid ambiguous storage rules; all paths must be deterministic.
