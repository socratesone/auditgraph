# Interfaces & UX

## Purpose
Define CLI/TUI/web UI scope, required commands, outputs, and integration surfaces.

## Source material
- [SPEC.md](SPEC.md) Interfaces
- [SPEC.md](SPEC.md) Graph Navigation & Visualization

## Decisions Required
- Interface preference (CLI-only, CLI+TUI, local web UI).
- Required CLI commands and flags.
- Machine-readable output formats and schemas.
- Minimum editor integration depth.

## Decisions (filled)

### Interface Preference

- CLI-first
- Optional local web UI later

### CLI Command Set

- init, ingest, extract, link, index, query, node, neighbors, diff, export, jobs, rebuild, why-connected

### Output Formats and Schemas

- JSON for machine-readable outputs
- Human-readable summaries to stdout

### Editor Integration Depth

- Open results and insert links (phase 2+)

## Resolved

- CLI-first with optional local web UI
- Required CLI command set
- JSON output schema requirement
- Editor integration depth defined

## Resolved
- None yet.
