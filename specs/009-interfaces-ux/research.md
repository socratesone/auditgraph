# Research: Interfaces and UX

## Decision 1: Interface Preference

- **Decision**: CLI-first with optional local web UI later.
- **Rationale**: Matches MVP scope and offline-first workflow.
- **Alternatives considered**: CLI + web UI day 1. Rejected due to scope and determinism constraints.

## Decision 2: CLI Command Set

- **Decision**: Required commands: init, ingest, extract, link, index, query, node, neighbors, diff, export, jobs, rebuild, why-connected.
- **Rationale**: Covers ingestion, search, graph traversal, and exports in MVP.
- **Alternatives considered**: Smaller command set. Rejected due to missing workflows.

## Decision 3: Output Formats

- **Decision**: JSON for machine-readable outputs and human-readable summaries to stdout.
- **Rationale**: Supports automation and interactive CLI usage.
- **Alternatives considered**: JSON-only. Rejected due to poor usability.

## Decision 4: Editor Integration Depth

- **Decision**: Open results and insert links (phase 2+).
- **Rationale**: Keeps MVP CLI-first while acknowledging integration needs.
- **Alternatives considered**: Full editor integration in MVP. Rejected due to scope.

## Decision 5: Error Reporting

- **Decision**: CLI commands return non-zero exit codes on errors and provide structured error payloads in JSON mode.
- **Rationale**: Enables automation to detect failures deterministically.
- **Alternatives considered**: Human-readable errors only. Rejected due to automation needs.
