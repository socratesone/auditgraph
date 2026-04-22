# 028 Markdown Extraction Adjustments 3

This file is a **non-normative review artifact**. It records the final pre-implementation analysis findings after `adjustments2.md` was applied. Use these instructions to update the normative spec artifacts before assigning implementation work.

Normative artifacts are:

- `spec.md`
- `data-model.md`
- `research.md`
- `plan.md`
- `tasks.md`
- `quickstart.md`
- every file under `contracts/`
- every file under `checklists/`

Review artifacts such as `adjustments.md`, `adjustments2.md`, and this file intentionally quote stale terminology and MUST be excluded from consistency grep checks.

## P0 - Remaining Implementation Blockers

### 1. Fix markdown-it-py linkify configuration everywhere

Problem: the spec currently gives inconsistent and partly incorrect parser setup instructions. Some files say `MarkdownIt("commonmark").enable("linkify")`; another says `linkify=True` on the constructor. Bare URL detection requires the linkify option, the linkify rule, and the `linkify-it-py` dependency.

Required edits:

- Update `contracts/markdown-subentities.md`, `tasks.md`, `research.md`, and any parser examples to use one authoritative adapter:

  ```python
  MarkdownIt("commonmark", {"linkify": True}).enable("linkify").parse(text)
  ```

- Keep `markdown-it-py[linkify]>=4,<5` as the dependency declaration, or declare `markdown-it-py>=4,<5` plus `linkify-it-py>=2,<3` explicitly. Do not rely on transitive `rich` dependencies.
- Add a test that fails if `linkify-it-py` is absent or if bare URLs stay as text tokens.
- Update any prose that says `.enable("linkify")` alone is sufficient.

Acceptance check: a bare URL such as `https://example.com/x` emits a `link_open`/`link_close` token and becomes one `ag:reference` entity.

### 2. Add an explicit document-anchor input for root section links

Problem: `data-model.md` says top-level `contains_section` edges originate from the note entity, but the extractor signature does not receive the note entity ID. The extractor cannot safely derive it because note IDs depend on the note title/frontmatter behavior in `build_note_entity`.

Required edits:

- Choose one design and apply it consistently:
  - Preferred: add `document_anchor_id: str` or `note_entity_id: str` to `extract_markdown_subentities(...)`; the runner passes `note_entity["id"]` immediately after `build_note_entity`.
  - Alternative: keep the extractor unaware of note IDs and have the runner create root `contains_section` links after the extractor returns sections.
- Update `contracts/markdown-subentities.md`, `tasks.md`, `data-model.md`, and tests to reflect the chosen ownership.
- State that top-level sections attach to this document anchor; nested sections attach to their parent section.
- Do not have the extractor recompute the note entity ID from title or path.

Acceptance check: top-level `contains_section` links are deterministic and point from the actual note entity written in the same extract run.

### 3. Define behavior for pre-heading markdown content

Problem: references and technologies can appear before the first heading or in a markdown document with no headings. The current topology assumes every `references` and `mentions_technology` edge originates from an enclosing `ag:section`, but no such section exists in these cases.

Required edits:

- Define one explicit anchoring rule:
  - Preferred: pre-heading references and technologies attach to the document anchor/note entity.
  - Alternative: emit a synthetic root `ag:section` for pre-heading content.
  - Alternative: emit entities without section-origin links and document the absence.
- Update `data-model.md §2`, `contracts/markdown-subentities.md`, `spec.md` edge cases, and tests.
- Add tests for:
  - code span before first heading;
  - link before first heading;
  - markdown file with links/code but no headings.

Acceptance check: every emitted `ag:reference` and `ag:technology` has deterministic, documented topology even when no heading encloses it.

### 4. Build `DocumentsIndex` from current-run successful records only

Problem: `tasks.md` currently says to build `DocumentsIndex` by scanning every file under `documents/`. Old document records may remain on disk after a file is deleted, excluded, or no longer part of the current run. Scanning all documents can incorrectly classify stale targets as internal.

Required edits:

- Update `spec.md`, `contracts/markdown-subentities.md`, `data-model.md`, and `tasks.md` so `DocumentsIndex` is built from the current normalized ingest manifest records where `parse_status == "ok"`.
- The runner may read each current record's corresponding `documents/<doc_id>.json`, but it must not include document files that are not represented by the current run's successful records.
- Clarify that "internal" means "materialized for a current successful source in this run/profile", not merely "some JSON file still exists under `documents/`."
- Add tests where a stale document file exists on disk but its source is absent from the current ingest manifest; links to it must classify as `unresolved`.

Acceptance check: stale or excluded document artifacts never make a reference internal.

### 5. Remove ambiguity around document ID and source path inputs

Problem: the contract states `document_id = deterministic_document_id(source_path, source_hash)` using workspace-relative `source_path`, while current ingest code may create document IDs using the parser path. The implementation should not guess.

Required edits:

- Update `contracts/markdown-subentities.md` to say the runner passes the actual `document_id` from the persisted document payload or source metadata, not a recomputed value inside the extractor.
- Remove or soften the precondition that `document_id` must equal a specific helper call unless the spec also updates ingest to guarantee relative source paths are used consistently for document IDs.
- Define how the runner locates the document payload for a normalized ingest record:
  - either by reading source metadata written during ingest;
  - or by using a deterministic ID helper whose inputs are explicitly the same inputs used by ingest.
- Add an integration test that verifies `record["path"]`, `documents/<doc_id>.json :: document.source_path`, and `DocumentsIndex.by_source_path` agree on the same workspace-relative path.

Acceptance check: implementation never has to reverse-engineer the document ID from an ambiguous path representation.

### 6. Correct the pre-028 upgrade test flow

Problem: `tasks.md` still asks a test to call `run_extract` directly against a pre-028 workspace whose markdown document records lack `document.text`. That conflicts with the spec's new rule that extract must error on missing `text`; the one-time refresh belongs to ingest.

Required edits:

- Replace the direct `run_extract` pre-028 upgrade test with an end-to-end `run_ingest` then `run_extract` or full `auditgraph run` test.
- The fixture should include a pre-028 cached document without `text` and an unchanged source file on disk.
- Assert that ingest treats the cache as incomplete for that one markdown source, reparses it once, writes `document.text`, and records `source_origin="fresh"` for the migration run.
- Then assert extract emits markdown subentities from the refreshed record.
- Keep direct `run_extract` tests only for already-migrated records that include `document.text`, or for explicit error behavior when `text` is missing.

Acceptance check: SC-011 is proven through the ingest/cache layer, not by making extract tolerate invalid inputs.

### 7. Fix `ag:reference.canonical_key`

Problem: `data-model.md` still shows the reference `canonical_key` as the full source-scoped hash input. That contradicts the authoritative rule that stored `canonical_key` is human-readable and distinct from ID input.

Required edits:

- In `data-model.md §1.3`, change:

  ```json
  "canonical_key": "<source_hash + '::reference::' + target + '::' + order>"
  ```

  to something like:

  ```json
  "canonical_key": "<redacted raw href target>"
  ```

- Keep ID input as `<source_hash> + "::reference::" + <raw_target> + "::" + <order_within_doc>`.
- Clarify whether the stored canonical key uses the redacted target or pre-redaction raw target. Prefer redacted, because it is written to disk.
- Update tests so reference ID input and stored `canonical_key` are asserted separately.

Acceptance check: every entity example distinguishes `id_input` from stored `canonical_key`.

### 8. Resolve warning serialization shape

Problem: `contracts/stage-manifest-warnings.md` says persisted manifests serialize `"warnings": []` even when empty, while `tasks.md` says serializers include the field only when non-empty.

Required edits:

- Pick one rule and apply it everywhere.
- Recommended final rule:
  - `StageResult.detail["warnings"]` MAY be omitted when empty.
  - persisted `StageManifest.warnings` and `IngestManifest.warnings` are always serialized as a list, including `[]`.
- Update `tasks.md` T039 and any tests to match the chosen manifest behavior.
- Ensure `outputs_hash` excludes `warnings` regardless of whether the field is present or empty.

Acceptance check: tests treat absent live warnings and `[]` live warnings as equivalent, but persisted manifests always expose a stable top-level `warnings` key if that rule is chosen.

## P1 - Cross-Artifact Cleanup

### 9. Normalize throughput warning code names

Problem: `plan.md` still says `zero_entities_produced`, while the rest of the spec uses `no_entities_produced`.

Required edits:

- Replace `zero_entities_produced` with `no_entities_produced` in every normative artifact.
- Keep `empty_index` unchanged.

Acceptance check: grep normative files for `zero_entities_produced` returns no matches.

### 10. Remove stale extractor signatures

Problem: `plan.md` still describes `extract_markdown_subentities(source_path, source_hash, chunk_records, redactor, documents_index)`, which is obsolete.

Required edits:

- Update `plan.md` to match the final contract signature after resolving the document-anchor input.
- Ensure no normative artifact says the markdown extractor reads chunk records as its primary input.

Acceptance check: extractor inputs are consistent across `plan.md`, `contracts/markdown-subentities.md`, `tasks.md`, and `data-model.md`.

### 11. Remove stale package-data wording

Problem: `contracts/rule-pack-validator.md` still claims the root `config/` directory is shipped as-is and that packaging is already handled by `packages.find`.

Required edits:

- Replace that statement with the package-data design:
  - package resources live under `auditgraph/_package_data/config/...`;
  - `pyproject.toml` adds `[tool.setuptools.package-data]`;
  - top-level `config/` files are editable-checkout mirrors, not the wheel packaging mechanism.

Acceptance check: no normative text claims root `config/` is packaged as-is.

### 12. Rename `config_base` / `pkg_base` remnants to `workspace_root`

Problem: the rule-pack contract now uses `workspace_root`, but tasks and research still contain `config_base` or `pkg_base`.

Required edits:

- Update `tasks.md`, `research.md`, and `contracts/rule-pack-validator.md` examples so the validator API is consistently:

  ```python
  validate_rule_pack_paths(paths, workspace_root)
  ```

- Update test names such as `test_relative_path_resolves_against_config_base` if needed.
- Keep the explicit rule: relative config paths resolve against workspace root, not the config file's parent.

Acceptance check: normative files no longer use `config_base` or `pkg_base` for the rule-pack validator.

### 13. Fix stale canonical-key helper claim in research

Problem: `research.md` still says heading slugification matches the existing project `canonical_key` helper, while `data-model.md` explicitly says not to use that helper.

Required edits:

- Replace the claim with the inline slug rules from `data-model.md §1.0`.
- State that the existing helper is intentionally not used because markdown section keys are path-like nested slugs.

Acceptance check: normative files contain no claim that markdown slugification delegates to or matches `auditgraph.storage.ontology.canonical_key`.

### 14. Fix quickstart config restoration

Problem: quickstart step 8 says `auditgraph init --root .` restores a broken `config/pkg.yaml`, but scaffold init is idempotent and should not overwrite an existing config.

Required edits:

- Replace the restore step with one that actually restores the valid config, such as:
  - save a backup before overwriting and move it back after the negative test; or
  - rerun the rest of the quickstart in a new scratch directory; or
  - explicitly rewrite the known-good `config/pkg.yaml`.
- Do not rely on `auditgraph init` overwriting existing files unless the implementation intentionally changes scaffold semantics, which is not currently specified.

Acceptance check: quickstart can continue after the broken-config test without manual cleanup.

### 15. Strengthen the cooccurrence quickstart check

Problem: FR-016e says `ag:section`, `ag:technology`, and `ag:reference` are excluded from generic source cooccurrence links. The quickstart currently checks only whether both endpoints are markdown subentities.

Required edits:

- Update quickstart step 10 to flag a violation if **either** endpoint type is in `{ag:section, ag:technology, ag:reference}`.
- Update SC-013 or related prose if necessary so it does not imply only "both endpoints" are disallowed.

Acceptance check: no `link.source_cooccurrence.v1` link has either endpoint in the markdown subentity type set.

### 16. Fix fenced-code wording in FR-008

Problem: `spec.md` FR-008 still says fenced code block content, while FR-016g says fenced code blocks emit only the `info` string.

Required edits:

- Update FR-008 to say inline code spans and fenced code block info strings.
- Keep FR-016g as the detailed authoritative rule.

Acceptance check: no normative requirement implies fenced code block body content is mined for `ag:technology`.

## P2 - Clarifications Worth Adding Before Implementation

### 17. Specify how the opt-out flag affects pruning

Current task text says disabling `extraction.markdown.enabled` makes both the producer and pruner inert. This preserves existing markdown subentities on disk if a user disables the feature after using it.

Required edits:

- Confirm this is intentional in `spec.md` or `data-model.md`.
- If the desired behavior is "disabled means no markdown subentities remain", change the task so pruning still removes existing markdown subentities even when production is disabled.

Acceptance check: disabling markdown extraction has explicitly documented storage behavior.

### 18. Define reference/link target redaction order

Problem: the ID input uses raw target, while stored target/canonical key should be redacted. If redaction policy changes, stored values may change while IDs may or may not.

Required edits:

- Define whether `ag:reference` ID input is pre-redaction raw target or redacted target.
- Recommended: use the redacted target for both stored target and ID input, because the extractor receives already-redacted document text and should not reintroduce secret-bearing raw strings into deterministic IDs.
- Update tests for URL credential redaction accordingly.

Acceptance check: no credential-shaped substring can appear in IDs, canonical keys, targets, links, or test snapshots.

### 19. Add current-run document-index stale-artifact test to the reviewer checklist

Required edits:

- Add a reviewer checklist item requiring a test where `documents/` contains a stale document not present in the current ingest manifest.
- The expected result is `resolution="unresolved"` for links to that stale document path.

Acceptance check: final review explicitly guards against stale document artifacts influencing reference resolution.

## Final Verification Checklist

Before implementation starts, verify:

- `MarkdownIt("commonmark", {"linkify": True}).enable("linkify")` is the only parser setup shown in normative artifacts.
- `linkify-it-py` is guaranteed by dependency metadata and lockfile.
- Root section links have a valid document/note anchor input.
- Pre-heading links/code have documented topology.
- `DocumentsIndex` is built from current successful ingest records only.
- The extractor does not recompute document IDs from ambiguous paths.
- Pre-028 upgrade is tested through ingest refresh, not direct extract tolerance.
- Reference `canonical_key` is human-readable/redacted and distinct from ID input.
- Warning serialization rules are identical in contracts and tasks.
- No normative file contains `zero_entities_produced`, old extractor signatures, stale rule-pack packaging language, `config_base`/`pkg_base` validator semantics, or the old canonical-key-helper claim.
- Quickstart can run through the broken-config step and recover automatically.
- Cooccurrence exclusion checks fail if either endpoint is a markdown subentity.
