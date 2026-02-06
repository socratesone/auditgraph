# Spec Blueprint: Pipeline Stages

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable pipeline spec that defines stage contracts, manifests,
atomic write behavior, and recovery rules.

## Source material
- [SPEC.md](SPEC.md) Architecture, Pipeline stages

## Required decisions the spec must make
- Stage list and boundaries (ingest, normalize, extract, link, index, serve).
- Stage inputs, outputs, and manifest paths.
- Manifest schema and versioning.
- Atomic write order and recovery behavior.
- Stage dependency validation rules.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Stage contract table with inputs, outputs, entry/exit criteria, and manifest paths.
2) Manifest schema with required fields and versioning rules.
3) Atomic write and recovery behavior (temp paths, manifest last).
4) Deterministic stage ordering and run identifier propagation.
5) CLI or API triggers for each stage.
6) Test plan with at least:
	- manifest path correctness
	- dependency validation
	- recovery behavior when manifests are missing

## Definition of done for the spec
- The spec provides complete stage contracts for every stage in scope.
- The spec defines file paths and schemas that can be validated in tests.
- The spec includes acceptance criteria and tests that map to code changes.

## Guardrails
- Do not leave stages undefined or described only by intent.
- Avoid non-testable language; use MUST/SHALL for requirements.
