# Data Model: Security, Privacy, and Compliance Policies

**Branch**: 011-security-privacy-compliance  
**Date**: 2026-02-06  
**Spec**: [specs/011-security-privacy-compliance/spec.md](spec.md)

This feature introduces policy-controlled redaction and strict profile boundaries. The data model describes the minimum persistent metadata required to make redaction and exports auditable and deterministic.

## Entities

### Profile
Represents an isolated configuration + storage namespace.

**Fields**
- `name` (string): Active profile name.
- `pkg_root` (string): Computed path `.pkg/profiles/<name>/` (derived, not user-entered).

**Rules**
- `name` must be validated as a safe identifier (no path separators, no `..`).

---

### DataClassification
A label used to describe handling expectations.

**Fields**
- `class` (enum): `public | internal | sensitive | secret`

**Rules**
- Any detected secret material is classified as `secret`.

---

### RedactionPolicy
A versioned rule set used to detect and replace secret-like content.

**Fields**
- `policy_id` (string): Stable identifier, e.g. `redaction.policy.v1`.
- `version` (string): Semver-like version or monotonic tag.
- `enabled` (bool)
- `detectors` (array): Named detectors included in the policy.

**Rules**
- Policy version MUST be recorded in export metadata.

---

### RedactionSummary
Aggregated metadata describing what redactions were applied.

**Fields**
- `counts_by_category` (object): Map `{category -> count}`.
- `total_matches` (int)

**Optional fields (recommended)**
- `ids` (array of string): Deterministic redaction IDs (no raw secret text).

---

### ExportMetadata
Metadata embedded within exported artifacts.

**Fields (required)**
- `created_at` (string): ISO8601 timestamp.
- `profile` (string): Active profile name.
- `root_id` (string): Non-sensitive workspace identifier (e.g., normalized root path or hash).
- `redaction_policy_id` (string)
- `redaction_policy_version` (string)
- `redaction_summary` (RedactionSummary)
- `clean_room` (bool): Must be `true` for default exports.

**Rules**
- Must not contain raw secret material.

---

## Relationships

- **Profile 1—N Exports**: Exports are generated within a single active profile.
- **ExportMetadata 1—1 RedactionPolicy**: Export references the policy identifier and version.

## State Transitions

### Export
- `created` → `written`

**Invariants**
- If `clean_room=true`, export payload MUST be redacted.
- If redaction is disabled (explicit opt-in), export metadata MUST label the export as not safe to share.
