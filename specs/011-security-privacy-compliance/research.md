# Research: Security, Privacy, and Compliance Policies

**Branch**: 011-security-privacy-compliance  
**Date**: 2026-02-06  
**Spec**: [specs/011-security-privacy-compliance/spec.md](spec.md)

This document resolves implementation-relevant design decisions for a deterministic redaction + isolation system that does not leak secret content into derived artifacts or exports.

## Decisions

### Decision 1: Encryption at rest is environmental, not application-level
- **Decision**: Do not implement an internal encryption-at-rest layer. Users who require encryption at rest must place the workspace (including `.pkg/`) on encrypted storage.
- **Rationale**: Keeps artifacts diffable and deterministic; avoids complex key management and portability pitfalls.
- **Alternatives considered**:
  - App-managed encryption for `.pkg/` (stronger default, but large complexity and risk of breaking determinism/diffing).

### Decision 2: Deterministic, profile-scoped secret redaction
- **Decision**: Implement pattern-based secret detection (high-confidence, format-based rules first) and replace matches with deterministic markers.
- **Marker shape**: `<<redacted:{category}:{id}>>` where `{id}` is derived from a profile-scoped secret using an HMAC of the matched secret value (short prefix for readability).
- **Rationale**: Deterministic outputs for replay/diff; avoids offline guessing compared to plain hashes; prevents cross-profile correlation.
- **Alternatives considered**:
  - Plain `SHA256(secret)` identifiers (simpler but enables offline guessing for low-entropy secrets).
  - Random per-run identifiers (safer against correlation but breaks determinism).
  - Third-party scanners (broader coverage but harder to pin deterministically; version drift risk).

### Decision 3: Redact before persistence, indexing, export, and ID derivation
- **Decision**: Apply redaction at “choke points” before writing any derived artifact, and before deriving IDs/hashes from text fields.
- **Rationale**: Even if a secret is later removed from stored text, an ID/hash derived from raw secret-containing text becomes a persistent fingerprint.
- **Alternatives considered**:
  - Redact only exports (insufficient: secrets can leak into `.pkg/` artifacts and indexes).
  - Redact only display fields (insufficient: indexes/manifests/logs still leak).

### Decision 4: Path boundary enforcement for profile isolation
- **Decision**: Treat `active_profile` and any user/config-provided paths as untrusted input and enforce strict boundary checks:
  - Validate profile names (reject path separators, `..`, empty, overly long).
  - Confine artifact reads/writes to `.pkg/profiles/<active-profile>/...`.
  - Resolve paths (symlink-aware) and reject anything that escapes the allowed base.
- **Rationale**: Prevents cross-profile reads/writes and path-injection via profile name concatenation.
- **Alternatives considered**:
  - Sanitizing invalid profile names into “safe” slugs (more forgiving but potentially surprising).
  - Hashing profile names to directories (safe but less user-friendly).

### Decision 5: Export defaults are “clean-room” and include explicit metadata
- **Decision**: Exports are redacted by default and embed an `export_metadata` block with policy identifiers and redaction summary counts.
- **Rationale**: Exports are the most common sharing surface; metadata makes redaction auditable without reintroducing secrets.
- **Alternatives considered**:
  - Redaction optional by default (unsafe default).
  - Writing metadata only to CLI stdout (metadata must travel with the exported artifact).

### Decision 6: Export/job output path traversal protection
- **Decision**: For workspace-relative output paths, enforce “must remain under allowed export base” semantics, and fail closed on traversal attempts.
- **Rationale**: Prevents accidental or malicious writes outside intended directories (`../..`, absolute paths, symlink breakout).
- **Alternatives considered**:
  - Allow arbitrary absolute output paths (powerful but footgun; higher leak risk).

## Recommended MVP detection categories

High-confidence, format-based detectors first:
- Private keys (PEM-like blocks, OpenSSH key lines)
- JWTs and `Authorization: Bearer ...` header values
- Credentials embedded in URLs and common query parameter keys
- Common vendor token prefixes (e.g., GitHub/Slack/Stripe examples) where format is stable
- Key/value assignment contexts for `password`, `secret`, `token`, `api_key`, `client_secret`, `private_key` (redact value only)

## Non-goals

- Perfect secret detection. The goal is deterministic, testable reductions in risk with minimal false positives, expanded over time.
