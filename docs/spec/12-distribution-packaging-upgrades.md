# Distribution, Packaging & Upgrades

## Purpose
Define OS support, packaging model, migration policy, and performance budgets.

## Source material
- [SPEC.md](SPEC.md) I) Distribution and Maintainability
- [SPEC.md](SPEC.md) Non-Functional Requirements

## Decisions Required
- Target OS for day 1.
- Packaging preference (single binary, Python package, Docker optional, BYOR).
- Upgrade/migration policy (mutable vs immutable outputs).
- Disk footprint budget for indexes.

## Decisions (filled)

### Target OS

- Linux and macOS day 1

### Packaging Model

- Python package with console script

### Upgrade/Migration Policy

- Derived artifacts can be rebuilt
- Keep old outputs in versioned run folders

### Disk Footprint Budget

- Index footprint <= 2x source size

## Resolved

- OS support, packaging model, upgrade policy, and footprint budget defined

## Resolved
- None yet.
