# Spec Blueprint: Security, Privacy, and Compliance

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable security and privacy spec that defines required policies
for storage, redaction, and profile isolation.

## Source material
- [SPEC.md](SPEC.md) Security & Privacy
- [SPEC.md](SPEC.md) H) Privacy, Security, Compliance

## Required decisions the spec must make
- Encryption at rest requirements and scope.
- Secrets detection and redaction requirements.
- Profile isolation guarantees and query boundaries.
- Export redaction policy and clean-room sharing rules.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Data classification and storage handling rules.
2) Redaction policy with specific detection and handling behaviors.
3) Profile isolation rules with file path boundaries.
4) Export policy and required metadata for redacted outputs.
5) Test plan with at least:
	- profile isolation checks
	- redaction rules (if implemented)

## Definition of done for the spec
- The spec defines concrete behaviors that can be validated in tests.
- The spec includes acceptance criteria and tests that map to code changes.

## Guardrails
- Do not describe security goals without enforceable rules.
- Avoid ambiguous language; use MUST/SHALL for requirements.
