# Security, Privacy & Compliance

## Purpose
Define encryption, redaction, profile isolation, and export policy.

## Source material
- [SPEC.md](SPEC.md) Security & Privacy
- [SPEC.md](SPEC.md) H) Privacy, Security, Compliance

## Decisions Required
- Encryption at rest requirements and scope.
- Secrets detection/redaction policy.
- Multi-profile separation requirements.
- Export redaction and clean-room sharing policy.

## Decisions (filled)

### Encryption Policy

- Not required for source store
- Optional for exports

### Secrets Handling

- Automatic detection and redaction in derived artifacts and exports

### Profile Separation

- Separate profile roots
- No cross-profile queries

### Export Policy

- Support redaction profiles for clean-room sharing

## Resolved

- Encryption, secrets handling, profile separation, and export policy defined

## Resolved
- None yet.
