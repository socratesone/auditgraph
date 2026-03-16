# Data Model: PDF and DOC Ingestion

## Entities

### DocumentRecord
- `document_id` (string, stable)
- `source_path` (string)
- `source_hash` (string, SHA-256)
- `mime_type` (string)
- `file_size` (integer)
- `ingested_at` (timestamp)
- `extractor_id` (string)
- `extractor_version` (string)
- `ingest_config_hash` (string)
- `status` (`ok|skipped|failed`)
- `status_reason` (string, nullable)

### SegmentRecord
- `segment_id` (string, stable)
- `document_id` (string, FK)
- `order` (integer, stable order within document)
- `type` (enum: `page|paragraph|heading|list_item|table|other`)
- `text` (string, normalized)
- `page_start` (integer, nullable)
- `page_end` (integer, nullable)
- `paragraph_index` (integer, nullable)

### ChunkRecord
- `chunk_id` (string, stable)
- `document_id` (string, FK)
- `order` (integer)
- `text` (string)
- `token_count` (integer)
- `segment_ids` (array[string])
- `overlap_tokens` (integer)
- `source_path` (string)
- `source_hash` (string)
- `page_start` (integer, nullable)
- `page_end` (integer, nullable)
- `paragraph_index_start` (integer, nullable)
- `paragraph_index_end` (integer, nullable)

## Relationships

- `DocumentRecord 1 -> N SegmentRecord`
- `DocumentRecord 1 -> N ChunkRecord`
- `ChunkRecord N -> N SegmentRecord` (represented by `segment_ids`)

## Identity and Stability Rules

- `document_id` derived deterministically from canonical source identity (`source_path`) and current `source_hash`.
- `segment_id` derived from `document_id + type + order + normalized_text_hash`.
- `chunk_id` derived from `document_id + order + chunk_text_hash`.
- IDs must be stable across repeated runs on unchanged inputs.

## State Transitions

- `discovered -> ok`
- `discovered -> skipped`
- `discovered -> failed`

`skipped` and `failed` must always include `status_reason`.

## Validation Rules

- `.doc` in day-1 must produce `failed` or `skipped` with explicit unsupported reason.
- OCR default is `off`; when off, scanned/image-only no-text pages can fail/skip with explicit reason.
- Citation data must remain metadata-only; chunk text must not contain injected page markers.
- Token chunking and overlap must follow effective config and be deterministic.
