# Quickstart: PDF and DOC Ingestion

## Prerequisites

- Python environment active
- Auditgraph workspace initialized
- `config/pkg.yaml` profile includes `.pdf` and `.docx` in allowed extensions
- OCR default policy set to `off` (explicit opt-in only)

## 1) Prepare fixture inputs

Place sample files under an included path, for example:

- `docs/fixtures/sample.pdf`
- `docs/fixtures/sample.docx`

## 2) Import and ingest

```bash
auditgraph import docs/fixtures --root . --config config/pkg.yaml
auditgraph ingest --root . --config config/pkg.yaml
```

Expected behavior:
- PDF/DOCX files produce ingest artifacts
- `.doc` files are reported as unsupported in day-1 scope
- batch continues on per-file failures

## 3) Verify deterministic re-ingestion

Run ingest again without file changes:

```bash
auditgraph ingest --root . --config config/pkg.yaml
```

Expected behavior:
- unchanged files are skipped by hash
- skip reasons are explicit

## 4) Verify query citations (metadata-only)

```bash
auditgraph query --q "policy" --root . --config config/pkg.yaml
```

Expected behavior:
- results include source path/location metadata
- chunk text contains no inline page markers

## 5) Verify export/sync compatibility

```bash
auditgraph export --format json --root . --config config/pkg.yaml
auditgraph export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/docs.cypher
auditgraph sync-neo4j --root . --config config/pkg.yaml --dry-run
```

Expected behavior:
- provenance-bearing document/chunk records remain available in downstream outputs
