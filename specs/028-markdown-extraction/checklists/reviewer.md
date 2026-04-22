# Reviewer Acceptance Checklist: Spec-028

**Purpose**: Guardrail checklist applied by a reviewer during `/speckit.analyze` at the close of implementation. Derived from `adjustments.md §12` and tuned to the categories of drift that the pre-implementation review surfaced.

**When to run**: after all `tasks.md` items marked [ ] become [x], before opening a PR.

## Scope of "normative files"

When this checklist says "every artifact" or "across normative files", it means:

- `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`
- every file under `contracts/`
- `quickstart.md`
- every file under `checklists/` EXCEPT the present file and any review logs

It explicitly EXCLUDES:

- `adjustments.md`, `adjustments2.md`, and any further `adjustments*.md` files
- Draft working notes or scratch files outside `specs/028-markdown-extraction/`

Review logs intentionally quote obsolete terminology as historical context. Automated consistency checks (`grep`, ripgrep, the terminology scrub in §1 below) MUST use an include-list based on the above, or an exclude glob like `--exclude 'adjustments*.md'`. A CI grep that flags `references_document` inside `adjustments2.md` is a false positive.

---

## 1. Internal consistency across artifacts

- [ ] No ID-generation rule appears differently in `spec.md`, `data-model.md`, `research.md`, and `contracts/markdown-subentities.md`. (data-model.md §1.0 is the single source of truth.)
- [ ] No entity or link type is named inconsistently (e.g., `references` vs `references_document` vs `cross_reference`) across any artifact.
- [ ] No reference-resolution rule differs between `spec.md` (FR-016f), `data-model.md` §1.3, and `contracts/markdown-subentities.md`.
- [ ] No technology-token rule differs between `spec.md` (FR-016g/h), `data-model.md` §1.2, and `contracts/markdown-subentities.md`.
- [ ] The link topology table in `data-model.md §2` matches the topology described in `spec.md` Key Entities (Reference) and the rule IDs used in pruning per FR-016c/FR-016d.
- [ ] No canonical_key rule claims to "match the existing `auditgraph.storage.ontology.canonical_key` helper" unless `markdown.py` actually calls that helper.

## 2. Quickstart fidelity

- [ ] `quickstart.md` is executed mechanically end-to-end against a fresh scratch directory at least once.
- [ ] Every expected count in `quickstart.md §2` matches the actual output of the implementation against the stated fixture corpus.
- [ ] `quickstart.md §3` compares `outputs_hash` (not whole-manifest bytes) across runs.
- [ ] `quickstart.md §5` empty-pipeline demo uses a source that actually produces zero entities (a `.txt` file, not a `.md` file).
- [ ] `quickstart.md §6` uses `.results[0]` for list-response access (not `.items[0]`).
- [ ] Every command in quickstart runs without error; every exit code matches the documented expectation.

## 3. Data model authority

- [ ] Every entity type shipped by this spec (`ag:section`, `ag:technology`, `ag:reference`) has exactly one authoritative schema definition, in `data-model.md`.
- [ ] Every new link rule ID (`link.markdown.contains_section.v1`, `link.markdown.mentions_technology.v1`, `link.markdown.references.v1`, `link.markdown.resolves_to_document.v1`) is documented in `data-model.md §2` and referenced consistently in task descriptions and test names.
- [ ] Every invariant I1–I10 in `data-model.md §6` has at least one test assertion in `tests/test_spec028_*.py`.

## 4. Query / navigation coverage

- [ ] Every query the spec promises users can run against the new types (`auditgraph list --type ag:section`, `auditgraph list --type ag:technology`, etc.) has a concrete test that demonstrates it works on a real fixture.
- [ ] `auditgraph node <id>` resolves at least one `doc_*`, one `chk_*`, and one `ent_*` ID in tests.
- [ ] `auditgraph list` response uses the existing `results` key, not an invented `items` key.

## 5. Stale-entity pruning

- [ ] At least one test performs an edit (heading rename, code-token rename, link-target change) and asserts that the pre-edit entity is absent on the next run.
- [ ] At least one test asserts that non-markdown entity types (`note`, NER, git-provenance) survive the pruning pass unchanged.
- [ ] At least one test (per adjustments3.md §4 / §19) verifies that a stale `documents/<doc_id>.json` record left on disk from a prior run — whose source is NOT in the current ingest manifest — does NOT cause references to its path to classify as `internal`. The expected classification for a link targeting a stale path is `unresolved`, with no `resolves_to_document` edge emitted.

## 6. Cooccurrence scaling protection

- [ ] At least one test asserts that no `link.source_cooccurrence.v1` link has both endpoints in `{ag:section, ag:technology, ag:reference}`.
- [ ] The exclusion list in `auditgraph/link/rules.py` is exactly `{ag:section, ag:technology, ag:reference}` — no drift.

## 7. Packaging + init

- [ ] `pyproject.toml` `[tool.setuptools.package-data]` includes the new stub YAMLs.
- [ ] `auditgraph init` copies `pkg.yaml` AND both stub rule-packs into the workspace.
- [ ] The rule-pack validator falls back to package resources when workspace-local paths are absent.

## 8. Dependency pin

- [ ] `pyproject.toml` declares `markdown-it-py>=4,<5` (matches `uv.lock`).
- [ ] No research note still references `>=3,<4`.

## 9. Constitution adherence

- [ ] Every implementation task has an associated test that failed before the task and passes after (Constitution III).
- [ ] The Constitution IV refactor-audit tasks (T017, T036, T046, T057, T064, T072) were actually executed, not just checked off.
- [ ] `wall_clock_now()` is NOT imported or called from any hashable-output code path (Constitution V, Invariant I7).

---

## Outcome

Tick every box above. If any item remains unchecked, either:

- fix the underlying defect and re-run the offending test(s), OR
- document a deliberate deferral in the PR description with a link to the follow-up spec.

If no item can be deferred without violating the constitution, block the merge.
