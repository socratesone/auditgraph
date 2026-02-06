# Spec Blueprint: Knowledge Model

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable knowledge model spec that defines canonical entity/claim schemas,
namespacing, contradiction handling, and temporal validity.

## Source material
- [SPEC.md](SPEC.md) D) Knowledge Model
- [SPEC.md](SPEC.md) Data Model

## Required decisions the spec must make
- Canonical entity types and required fields.
- Claim schema (subject, predicate, object, provenance) and optional fields.
- Contradiction handling (explicit flagging and retention rules).
- Temporal validity rules and default behavior when missing.
- Confidence score policy and allowed sources of confidence.
- Ontology namespace rules and conflict resolution.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Entity and claim schemas with required fields and examples.
2) Namespacing rules and canonical key construction.
3) Contradiction flags and expected query behavior.
4) Temporal validity windows and how they are stored.
5) Confidence scoring rules for deterministic extraction.
6) Validation rules and error behavior for malformed records.
7) Test plan with at least:
	- schema validation for entities/claims
	- namespace resolution
	- contradiction flagging
	- temporal validity handling

## Definition of done for the spec
- The spec defines concrete JSON fields for every entity/claim type.
- The spec includes examples and validation rules that can be enforced in code.
- The spec includes acceptance criteria and tests that map to code changes.

## Guardrails
- Do not describe extraction rules here unless they impact schema.
- Avoid ambiguous type definitions; every field must be named and typed.
