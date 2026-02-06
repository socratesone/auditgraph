# Quickstart

## Configure day-1 ingestion

Update config/pkg.yaml to reflect day-1 sources and normalization rules:

```yaml
profiles:
  default:
    include_paths:
      - "notes"
      - "repos"
    exclude_globs:
      - "**/node_modules/**"
      - "**/.git/**"
    normalization:
      unicode: "NFC"
      line_endings: "LF"
      path_style: "posix"
```

## Run ingestion

```bash
auditgraph ingest --root . --config config/pkg.yaml
```

## Manual import

```bash
auditgraph import notes/adr/0001.md logs/ --root . --config config/pkg.yaml
```

## Notes
- Only Markdown/plain text and Git working tree files are in scope for day 1.
- Unsupported formats should be recorded as skipped with a reason.
