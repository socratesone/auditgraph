# 028 Markdown Extraction Adjustments 2

> **NON-NORMATIVE — review/change-control artifact.**
> This file is a review log. It quotes obsolete terminology from earlier spec drafts as historical context for reviewers. Consistency checks, lint sweeps, and terminology greps MUST exclude `adjustments*.md` — see `checklists/reviewer.md` for the authoritative scope of normative files.

These instructions convert the second re-evaluation findings into concrete spec edits. Apply them before implementation work begins. The goal is to make the 028 artifacts internally consistent, executable through the quickstart, and precise enough that an implementation agent does not have to infer missing behavior.

Treat `spec.md`, `data-model.md`, `contracts/`, `plan.md`, `tasks.md`, `research.md`, `quickstart.md`, and `checklists/` as normative. Treat `adjustments.md` and this file as review/change-control artifacts unless a task explicitly says otherwise.

## P0 - Resolve Implementation Blockers

### 1. Define the pre-028 cache migration path for `document.text`

Problem: the new extractor depends on markdown `document.text`, but existing cached document records from pre-028 workspaces will not contain that field. The spec also says existing cached workspaces should upgrade without reparsing unchanged sources. Those requirements conflict.

Required edits:

- Update `spec.md` FR-016a/FR-016b and any related compatibility language to define one explicit behavior.
- Recommended behavior: if a cached markdown document lacks `document.text`, treat that cached document as incomplete for markdown extraction and force a one-time reparse/redaction of the source on the next run. After that run, the document record includes `text` and extraction can operate without rereading the source.
- State that extraction itself still reads from cached document records only; the cache-refresh decision belongs to the ingest/cache layer.
- Update `data-model.md` and `contracts/ingest-record-v2.md` so markdown `document.text` is clearly required for 028-compatible cached markdown document records and absent/optional for non-markdown records.
- Update `tasks.md` legacy-cache tests so the fixture either includes `document.text` when testing pure extraction, or verifies that missing `document.text` causes the ingest/cache layer to refresh the markdown source once.
- Add acceptance criteria:
  - legacy markdown cache without `document.text` refreshes once and then emits markdown subentities;
  - markdown cache with `document.text` emits subentities without rereading source bytes;
  - non-markdown cached documents are unaffected.

### 2. Fix the quickstart so it can actually run

Problem: the quickstart currently creates markdown files at the scratch root, but the default project config may not ingest root files. It also writes a broken `pkg.yaml` in the wrong location for default config resolution, and one link check references fields not present in the link schema.

Required edits:

- Make the initial quickstart setup deterministic. Use one of these approaches and apply it consistently:
  - create markdown files under a directory included by the generated default config, such as `notes/`; or
  - explicitly write `config/pkg.yaml` with `include_paths: ["."]` before running `auditgraph run`; or
  - pass `--config pkg.yaml` everywhere if keeping a root-level config.
- Update the broken-config step to modify the config file actually used by the CLI. Prefer overwriting `config/pkg.yaml` instead of creating root `pkg.yaml`.
- Replace any `jq` checks using `.from_type` or `.to_type`. Current link records expose endpoint IDs and link type, not endpoint type fields. Either:
  - inspect endpoint entity records by `from_id`/`to_id`; or
  - explicitly add `from_type`/`to_type` to the link schema and update `data-model.md`, contracts, and tests accordingly.
- Make expected counts either exact or deliberately bounded, not both. If the count is approximate because existing link rules may add links, explain the reason and use a range.
- Ensure the empty-workspace smoke test uses `.txt` or disables every entity producer that would otherwise emit a note/document entity.

Acceptance check: a fresh user should be able to copy the quickstart into an empty scratch directory and complete it without editing commands by hand.

### 3. Specify how markdown-generated links are pruned

Problem: the spec says to delete links whose from-side or to-side `source_path` matches the refreshed source, but link records do not inherently store endpoint source paths. The implementation needs an explicit lookup rule.

Required edits:

- Define the pruning algorithm in `data-model.md`, `spec.md`, and the relevant contracts.
- Recommended behavior:
  - before emitting new markdown subentities for a changed markdown source, load existing markdown-generated entities for that `source_path`;
  - delete markdown-generated links whose `from_id` or `to_id` matches those entity IDs;
  - additionally delete `resolves_to_document` links from reference entities in that source;
  - do not delete unrelated global links or links generated by non-markdown producers unless their endpoint is one of the pruned markdown-generated entity IDs.
- Define the markdown-generated link types covered by pruning: `contains_section`, `has_technology`, `references`, and `resolves_to_document`.
- If the implementation instead relies on link evidence or stored endpoint metadata, add that metadata to the link schema and update all examples/tests.

Acceptance check: after editing a markdown file, stale section/reference/technology entities and their markdown-generated links disappear, while links for unchanged sources remain.

### 4. Resolve rule-pack path semantics

Problem: the spec mixes `config/extractors/...` paths with language saying paths are relative to the config file parent. For a config at `config/pkg.yaml`, that can resolve to `config/config/extractors/...`.

Required edits:

- Choose one path resolution rule and apply it everywhere.
- Recommended behavior: `rule_packs[].path` values are workspace-root-relative unless absolute. Package fallback is attempted only after the workspace path does not exist.
- Update `contracts/rule-pack-validator.md`, `tasks.md` T053, `quickstart.md`, and any config examples to match the selected rule.
- If choosing config-file-relative paths instead, change all examples from `config/extractors/...` to `extractors/...` and make sure inline config behavior is explicitly defined.
- Remove or replace stale language claiming that the root `config/` directory is already packaged as-is. The new design should use explicit package data or `importlib.resources` fallback.

Acceptance check: the default initialized config can find both local stub rule packs and packaged fallback rule packs without producing duplicate `config/config/...` paths.

## P1 - Remove Cross-Artifact Drift

### 5. Replace obsolete reference link terminology

Problem: several artifacts still mention `references_document` or `references_external`, while the updated topology uses `references` and `resolves_to_document`.

Required edits:

- Update `plan.md`, `tasks.md`, `contracts/markdown-subentities.md`, `research.md`, checklist files, and examples so normative files use only:
  - `references` for `section -> reference`;
  - `resolves_to_document` for `reference -> document`.
- Remove old wording that says links point to "`documents_index` keys for `references_document`".
- Update success criteria, task names, and examples so they describe the unified topology.
- If `adjustments.md` keeps old terminology as historical review context, label it non-normative and exclude `adjustments*.md` from consistency grep checks.

Acceptance check: in normative files, no obsolete `references_document` or `references_external` terms remain.

### 6. Correct ID and `canonical_key` examples

Problem: `data-model.md` still shows IDs as `sha256_text(canonical_key)` even though the updated design separates human-readable `canonical_key` from ID hash input.

Required edits:

- In `data-model.md`, replace example IDs like `ent_<sha256_text(canonical_key)>` with `ent_<sha256_text(id_input)>` or an equivalent name.
- Add or keep a short authoritative definition of `id_input` for each markdown subentity type.
- Ensure reference examples show `canonical_key` as the human-readable target key, not the full source-hash/type/order hash input.
- Update `research.md` so the table labels the hash material as `id_input` or "hash input", not "Canonical key".
- Remove language saying markdown slugification matches the existing project `canonical_key` helper if the new design intentionally does not use that helper.

Acceptance check: a reader can distinguish the stable ID hash input from the stored `canonical_key` field in every example.

### 7. Align function contracts with the new data flow

Problem: `contracts/markdown-subentities.md` still has some stale or impossible preconditions.

Required edits:

- Update the extractor signature everywhere to match the final design. If extraction reads document records, do not leave old signatures based on chunk records only.
- Replace `source_hash equals sha256_file(source_path)` as an extractor precondition with "caller guarantees `source_hash` corresponds to the original source bytes." The extractor should remain pure and should not need filesystem access to verify this.
- Ensure the contract says extractor input includes redacted markdown `document.text`, a `DocumentsIndex`, and enough metadata to emit source-scoped IDs.
- Update postconditions to refer to returned entity IDs and `DocumentsIndex.by_doc_id` / `DocumentsIndex.by_source_path`, not old link names.

Acceptance check: the contract can be implemented without rereading source files or recomputing file hashes inside the extractor.

### 8. Update stage warning contracts

Problem: warning placement is now specified as `StageResult.detail["warnings"]` plus manifest-level warnings, but the warning contract still emphasizes top-level payload warnings in some places.

Required edits:

- Update `contracts/stage-manifest-warnings.md` so live stage results store warnings under `StageResult.detail["warnings"]`.
- Specify exactly how those warnings are copied or summarized into the run manifest.
- Update CLI behavior so it reads the actual stage result/manifest shape.
- Fix zero-warning tests so they do not accidentally emit note/document entities when the test expects an empty pipeline.

Acceptance check: a malformed markdown input produces a visible extract-stage warning and a manifest warning; an intentionally empty `.txt`-only pipeline produces zero warnings.

### 9. Update plan and task ownership

Problem: `plan.md` still says some files require no change even though the new design requires parser/cache/config updates.

Required edits:

- Update the implementation plan to include changes to the parser or ingest record builder that writes markdown `document.text`.
- Add tasks for cache invalidation/migration when cached markdown document records are missing `text`.
- Add tasks for rule-pack package-data fallback and initialized stub copying.
- Add tasks for markdown link pruning and source-level cooccurrence exclusions.
- Update task dependencies so quickstart fixes, contracts, and migration tests happen before implementation tasks that depend on them.

Acceptance check: the task list fully covers every normative behavior in the spec and contracts.

## P2 - Clarify Edge Cases and Dependencies

### 10. Define heading parent behavior for documents that start below H1

Problem: the spec says `parent_section_id` is null for H1 but does not define what happens when a document starts with H2/H3.

Required edits:

- Define parent selection as "nearest preceding heading with a lower numeric heading level; otherwise `null`."
- Add examples for:
  - normal H1 -> H2 nesting;
  - document starts with H2;
  - skipped levels such as H1 -> H3.

Acceptance check: parent assignment is deterministic for every heading sequence.

### 11. Make markdown linkification dependencies explicit

Problem: bare URL capture depends on parser configuration and may require `linkify-it-py`.

Required edits:

- In `spec.md`, `plan.md`, and dependency/task files, specify the exact markdown-it-py configuration required for bare URL capture.
- Add `linkify-it-py` as an explicit dependency if needed.
- Add a contract or unit test proving that a bare URL such as `https://example.com/path` emits a reference.

Acceptance check: bare URLs, inline markdown links, and reference-style links are all covered by tests.

### 12. Reconcile "existing record shapes unchanged" with `document.text`

Problem: some prose says existing record shapes remain unchanged, but markdown document records now gain a `text` field.

Required edits:

- Update `data-model.md` and `spec.md` to say existing non-markdown record shapes remain unchanged.
- State that markdown document records are extended with redacted `text` as part of 028.
- Clarify whether `text` is required, optional, or absent for each document kind.

Acceptance check: there is no contradiction between compatibility language and the new markdown document payload.

### 13. Mark review adjustment files as non-normative

Problem: `adjustments.md` and `adjustments2.md` intentionally contain obsolete terms as review history. Simple grep-based consistency checks may flag them.

Required edits:

- Add a short note to the top of `adjustments.md` and this file saying they are non-normative review artifacts.
- Update reviewer checklist commands to search normative files only, or explicitly exclude `adjustments*.md`.

Acceptance check: automated or manual consistency checks do not fail because historical review notes quote obsolete terminology.

## Final Verification Checklist

Before handing 028 to an implementation agent, verify:

- Normative files use only `references` and `resolves_to_document` for markdown reference topology.
- `document.text` cache behavior is defined for new, existing, markdown, and non-markdown document records.
- Quickstart commands run from a fresh scratch directory without hidden assumptions.
- Rule-pack paths resolve exactly once and do not produce `config/config/...`.
- Link pruning can be implemented from fields or lookups explicitly described in the spec.
- Data-model examples distinguish `id_input` from stored `canonical_key`.
- Warning shape is consistent between `StageResult`, manifest, CLI output, and tests.
- Dependency and parser configuration for bare URL linkification are explicit.
- Legacy-cache, changed-source pruning, unchanged-source stability, and empty-pipeline tests are all represented in `tasks.md`.
