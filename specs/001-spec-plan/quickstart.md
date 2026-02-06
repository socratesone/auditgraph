# Quickstart

## Install (editable)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Initialize

```bash
auditgraph init --root .
```

## Run (placeholder commands)

```bash
auditgraph ingest --root . --config config/pkg.yaml
auditgraph extract
auditgraph link
auditgraph index
auditgraph query --q "symbol-name" --root . --config config/pkg.yaml
auditgraph node <entity_id> --root . --config config/pkg.yaml
auditgraph neighbors <entity_id> --depth 2 --root . --config config/pkg.yaml
auditgraph export --format json --root . --config config/pkg.yaml
auditgraph jobs list
auditgraph jobs run daily_digest --root . --config config/pkg.yaml
```

## Notes
- Pipeline commands are present as placeholders; implementations follow phased milestones.
- Deterministic outputs and audit manifests are required for all stages.
- Artifacts are stored under .pkg/profiles/<profile>/ to keep profiles isolated.
