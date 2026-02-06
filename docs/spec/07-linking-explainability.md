# Spec Blueprint: Linking and Explainability

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable linking spec that defines deterministic rules, explainability payloads,
and backlink behavior.

## Source material
- [SPEC.md](SPEC.md) Linking and Navigation
- [SPEC.md](SPEC.md) Search explainability

## Required decisions the spec must make
- Link generation policy (authoritative deterministic vs optional suggestions).
- Supported link types and required metadata fields.
- Explainability payload schema and evidence requirements.
- Backlinks strategy (on demand vs stored) and ordering rules.
- Conflict handling when multiple rules produce links.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Link rule list with rule ids and deterministic inputs.
2) Link artifact schema with required fields and authority flags.
3) Explainability payload schema with evidence references.
4) Backlink retrieval rules and ordering.
5) Link index or adjacency storage location.
6) Test plan with at least:
	- deterministic link generation
	- explainability payload presence
	- stable ordering for backlinks

## Definition of done for the spec
- The spec defines exact JSON fields for links and explanations.
- The spec includes concrete rule ids and example evidence references.
- The spec includes acceptance criteria and tests that map to code changes.

## Guardrails
- Do not leave linking rules undefined or described only by intent.
- Avoid ambiguous link types; list explicit supported types.
