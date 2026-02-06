# Data Model

## Entities

### Source
- Represents an ingested file with path, format type, parse status, and hashes.
- Key fields: path, source_hash, size, mtime, parser_id, parse_status.

### IngestionPolicy
- Represents the allowed sources, excluded formats, and capture channels.
- Key fields: allowed_sources, excluded_sources, capture_channels.

### FrontmatterSchema
- Represents canonical Markdown metadata fields.
- Key fields: title, tags, project, status.

## Validation Rules
- Only allowed sources are ingested; excluded sources are logged as skipped.
- Parse status must be present for every discovered file.
- Frontmatter fields are normalized; missing fields remain empty.

## State Transitions
- Discovered → Ingested (allowed sources)
- Discovered → Skipped (unsupported source with reason)
