# Quickstart

## Verify determinism

```bash
auditgraph ingest --root . --config config/pkg.yaml
# Run again and compare manifests in .pkg/profiles/<profile>/runs
```

## Notes
- Deterministic runs should produce identical manifests for identical inputs.
- Replay logs should capture stage metadata and input counts.
