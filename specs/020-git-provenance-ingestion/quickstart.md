# Quickstart: Git Provenance Ingestion

## Enable Git Provenance

Add to your profile in `config/pkg.yaml`:

```yaml
profiles:
  default:
    git_provenance:
      enabled: true
```

## Run Ingestion

```bash
# Full rebuild including Git provenance
auditgraph rebuild --root /path/to/repo

# Or run Git provenance stage alone (after ingest)
auditgraph git-provenance --root /path/to/repo
```

## Query Provenance

```bash
# Who changed this file?
auditgraph git-who src/auth.py --root .

# What commits touched this file?
auditgraph git-log src/auth.py --root .

# When was this file introduced?
auditgraph git-introduced src/auth.py --root .

# Full provenance summary
auditgraph git-history src/auth.py --root .
```

## Configure Commit Budget

```yaml
profiles:
  default:
    git_provenance:
      enabled: true
      max_tier2_commits: 1000    # Tier 2 budget (Tier 1 is unbounded)
      hot_paths:                 # Always include commits touching these
        - "package.json"
        - "pyproject.toml"
      cold_paths:                # Deprioritize these in scoring
        - "*.lock"
        - "*-lock.json"
        - "*.generated.*"
```

## How Commit Selection Works

1. **Tier 1 (always included)**: Tagged commits, root commits, merge branch points, branch heads, commits touching hot-path files. Tier 1 is unbounded — total ingested commits may exceed `max_tier2_commits`.
2. **Tier 2 (budget-filled)**: Remaining commits scored by `files_changed + (lines_changed / 400)`, highest scores first.

The most recent and earliest commits are always included in Tier 2 for diff-ability.
