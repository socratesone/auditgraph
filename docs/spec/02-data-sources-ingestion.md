# Spec Blueprint: Data Sources and Ingestion

## Intent (read first)
This document defines what the actual specification must include. It is not the specification itself.
The spec produced from this blueprint must be implementable in code and validated by tests.

## Goal
Produce a concrete, testable spec for ingestion that covers day-1 sources, allowed extensions,
capture channels, normalization rules, and deterministic skip behavior.

## Source material
- [SPEC.md](SPEC.md) B) Data Sources and Formats
- [SPEC.md](SPEC.md) Solution Space: Ingestion

## Required decisions the spec must make
- Day-1 source types and exact allowed file extensions.
- Code file inclusion and symbol extraction depth.
- PDF/OCR support policy (day-1 explicit include or exclude).
- Structured source inclusion (OpenAPI, Terraform, CI configs, JSON/YAML manifests).
- Capture channels (scan, manual import, watchers, plugins).
- Frontmatter normalization rules and fallback behavior.
- Skip reasons and required reporting fields for unsupported sources.

## Required spec sections and outputs
The spec MUST include the following, with concrete requirements and examples:

1) Scope and non-goals for day-1 ingestion.
2) Exact allowlist of file extensions and parser IDs.
3) Capture channels and CLI behavior (scan vs import).
4) Normalization rules for Markdown frontmatter with required keys.
5) Source artifact schema and required fields for skipped files.
6) Determinism rules (ordering, hashing, stable identifiers).
7) Error handling and skip reporting (no silent drops).
8) Test plan with at least:
	- allowlist/denylist tests
	- deterministic file discovery ordering
	- frontmatter parsing behavior
	- skipped-file reporting

## Definition of done for the spec
- The spec produces implementable requirements, not meta-instructions.
- The spec names concrete CLI commands and config fields.
- The spec includes acceptance criteria and test cases that map to code changes.
- A reviewer can implement ingestion without interpreting additional documents.

## Guardrails
- Do not restate this blueprint as the spec.
- Every requirement must be phrased as system behavior, not as a question or suggestion.
