# Quickstart: Security, Privacy, and Compliance Policies

**Branch**: 011-security-privacy-compliance  
**Date**: 2026-02-06  
**Spec**: [specs/011-security-privacy-compliance/spec.md](spec.md)

This quickstart describes the intended user workflow after implementing the policies in this spec.

## 1) Create a workspace and run ingest

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

auditgraph init --root .
auditgraph ingest --root . --config config/pkg.yaml
```

## 2) Verify profile isolation

- Create or select two profiles (e.g., `work` and `personal`) and run `ingest` under each.
- Run queries under profile A and confirm results are derived only from profile A artifacts.

## 3) Create a clean-room export

```bash
auditgraph export --format json --root . --config config/pkg.yaml
```

Expected properties of the exported JSON:
- Contains an `export_metadata` block.
- `export_metadata.clean_room` is `true` by default.
- Contains a `redaction_summary` with counts.
- Contains no raw secret substrings from ingested inputs.

## 4) Path safety expectations

- Workspace-relative output paths must not be able to escape the allowed export base via `..` traversal.
- If an unsafe output path is provided, the command should fail closed with a clear error.
