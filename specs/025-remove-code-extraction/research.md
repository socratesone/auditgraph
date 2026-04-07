# Research: Remove Code Extraction, Migrate File Entity Creation to Git Provenance

**Date**: 2026-04-07
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

This research file documents the technical decisions that fed into the plan, with rationale and alternatives considered. All decisions are grounded in actual code reads from the existing project; no speculation.

## R1: Where should the new file entity creator live?

**Decision**: Add `build_file_nodes(selected_commits, repo_path)` to `auditgraph/git/materializer.py` alongside the other entity-builder functions.

**Rationale**:
- The git materializer already has a consistent pattern: `build_commit_nodes`, `build_author_nodes`, `build_tag_nodes`, `build_repo_node`, `build_ref_nodes`. Adding `build_file_nodes` matches the existing convention exactly.
- The data the function needs (`selected_commits[i].files_changed`) is already populated upstream in `auditgraph/git/selector.py:SelectedCommit` (verified at `selector.py:34`). No new data flow needed.
- The function `build_links()` in the same file already iterates `c.files_changed` to construct `modifies` link `to_id` values via `entity_id(f"file:{file_path}")`. The new function uses identical ID derivation, guaranteeing the IDs match.
- Constitutional SRP: git provenance owns "things derived from git history". File paths in commits are derived from git history. Therefore the git provenance materializer is the right home.

**Alternatives considered**:
- *New module `auditgraph/git/file_entities.py`*: Rejected. Adds a one-function module for no benefit; the existing materializer already has 6 builders and one more doesn't crowd it.
- *Generic file-entity builder in `auditgraph/storage/`*: Rejected. The file entity is a git-provenance concept now (it represents a path that appeared in git history). Storage is a transport layer, not a domain layer.
- *Inline the entity creation inside `build_links()`*: Rejected. Mixes two concerns (link construction + entity construction). Existing builders are uniformly single-purpose; breaking that pattern would be inconsistent.

## R2: How should `build_file_nodes` derive file entity IDs?

**Decision**: Use `entity_id(f"file:{file_path}")` exactly as `build_links()` already does. The `file_path` comes from each `selected_commit.files_changed` list, which is the same source `build_links()` uses.

**Rationale**:
- Verified empirically during the spec verification phase: `entity_id("file:auditgraph/extract/ner.py")` returns the same hash regardless of which code path called it. Both `extract_code_symbols` (today) and `build_links` (today) and `build_file_nodes` (after this change) compute the same ID for the same path.
- This is the only way to make the file entity created in Phase A match the existing `modifies` link `to_id` references that git provenance has been emitting all along. Any other ID derivation would create a parallel entity universe and not fix the dangling-reference bug.
- The canonical key format (`file:<path>`) is established in two places (`extract/code_symbols.py:21` and `git/materializer.py:188`) with identical construction. There is no risk of mismatch.

**Alternatives considered**:
- *Hash the source content*: Rejected. The file entity represents a path in git history, not the current file content. Content-hash IDs would change every time the file is edited, breaking the link to commits that touched the older content.
- *Use a SHA from git*: Rejected. Git tracks blob SHAs per content version, but the file entity is path-scoped, not content-scoped. Multiple commits modify the same path with different content; the entity should be a single node with multiple `modifies` edges, not many entities.
- *Composite ID `file:<repo>:<path>`*: Rejected. Adds complexity for no current benefit. Cross-repo workspaces are not in scope; if they ever are, the ID can be migrated then.

## R3: How should `build_file_nodes` handle path deduplication and ordering?

**Decision**: Collect paths into a `set` during the walk (deduplicates), then sort the set alphabetically before constructing entity dicts. The output list is sorted by entity ID for the same reason `build_commit_nodes` and friends produce sorted output.

**Rationale**:
- Deduplication is required by FR-005 (a path touched by 100 commits becomes 1 entity, not 100). A set is the obvious data structure.
- Determinism is constitutional. The set itself is unordered in Python, so we MUST sort before returning, otherwise two runs of the same input could produce different output orderings, causing different `outputs_hash` values and breaking replay.
- Sorting by entity ID (rather than by path string) matches the convention used by `build_commit_nodes` and `build_author_nodes` which sort by their respective IDs.

**Alternatives considered**:
- *Insertion-order-preserving dict (Python 3.7+)*: Plausible, but the iteration order of `selected_commits` itself is deterministic only if `selector.py` produces sorted output (which it does, but the dependency is implicit). A set + explicit sort decouples our determinism guarantee from the upstream behavior.
- *Sort by path string instead of entity ID*: Functionally equivalent but inconsistent with the other builders. Pick one convention and stick to it.
- *No sort, rely on Python's set iteration order*: Rejected. CPython 3.7+ has insertion-order-stable dicts but not sets. A set's iteration order can change between runs even on the same data due to hash randomization (`PYTHONHASHSEED`).

## R4: Should file entity creation be optional or mandatory in `run_git_provenance`?

**Decision**: Mandatory. Whenever git provenance runs, file entities are produced for every path in the selected commits' files-changed lists. No config flag to disable.

**Rationale**:
- Producing the entities is cheap (a set walk over already-loaded data). The cost-benefit analysis doesn't justify a feature flag.
- A flag would create a third state to test (flag off + provenance on) that produces a graph with `modifies` links pointing at nonexistent entities — i.e., it would re-introduce the bug we're fixing. The right way to opt out of file entities is to disable git provenance entirely, which is already an option.
- YAGNI: no use case requires file entities to be off when commits are on.

**Alternatives considered**:
- *Add `git_provenance.materialize_file_entities: bool` config*: Rejected. Pure overhead. Tested-state-space cost (3 states instead of 2). No use case.
- *Make it implicit on a `--full` flag*: Same problem.

## R5: What happens to the existing `file` entity files on disk when an old workspace is rebuilt with the new code?

**Decision**: They are silently overwritten by the new entities. Same ID → same shard path → same on-disk filename → `write_json` truncates and rewrites. No special migration.

**Rationale**:
- Both old (`extract_code_symbols`) and new (`build_file_nodes`) creators produce the same ID for the same path AND the same field shape (per clarification Q1). The on-disk files become byte-identical for any path that exists in both runs.
- Paths that exist in the old workspace but NOT in git history (e.g., a `.py` file that was never committed) remain on disk as orphans because the new code never visits them. This is the same orphan situation that exists today for any deleted entity, and is consistent with the project's existing rebuild contract (no orphan sweeping).
- A user who wants a guaranteed-clean state runs `rm -rf .pkg && auditgraph init && auditgraph rebuild`. This is documented in the spec.

**Alternatives considered**:
- *Sweep orphans during rebuild*: Rejected. Pre-existing concern, not introduced by this spec. Touching it expands scope and risks deleting user data.
- *Migration script that detects and removes old code-only file entities*: Rejected. Same reason. The honest answer is "rebuild from clean if you want clean."
- *Refuse to overwrite if content differs*: Rejected. The content shouldn't differ if Q1's schema commitment is honored. If it does differ, that's a bug to fix, not a guard to add.

## R6: Should Phase A and Phase B be one commit or two?

**Decision**: Two commits on a single branch. Phase A first, Phase B second.

**Rationale**:
- Phase A is independently valuable: it fixes the pre-existing dangling-reference bug. If Phase B were ever deferred or rolled back, Phase A could stand alone.
- Phase B is destructive: it deletes a file, removes parser routes, and removes a config field. These deletions are safe ONLY because Phase A guarantees the data they were producing now comes from elsewhere. Splitting the commits makes the dependency explicit.
- The combined diff for one commit would be ~30 file touches and ~600 lines of churn. Splitting reduces reviewer cognitive load.
- If we discover a problem with the deletions during review, we can revert Phase B independently without losing Phase A's bug fix.

**Alternatives considered**:
- *One squash commit*: Rejected for the reviewability reason above.
- *Three commits (Phase A, deletions, docs)*: Plausible but doesn't add much value. The deletions and docs are tightly coupled — both serve the scope-narrowing decision and should land together.
- *Separate branches with separate PRs*: Rejected. The two phases are designed as a unit; splitting branches would force the reviewer to mentally re-merge them. One branch with two commits delivers the same review benefit at lower coordination cost.

## R7: Are there hidden code paths that read `file` entities from disk?

**Decision**: Verified by grep — 16 sites in tests that touch `type=file`. No production code (outside the tests themselves) does anything beyond what's already covered:
- BM25 indexer reads `entity.get("name")` and `entity.get("aliases")` — both fields are present in the new schema.
- The Spec 023 query layer reads `entity.get("type")` for `--type` filtering — present.
- The neighbors traversal reads link `to_id` and looks up the target entity by ID — works for all paths in git history after Phase A.
- The list/sort/aggregate engine reads arbitrary entity fields per `--where` predicates — `source_path` is preserved, and no new fields are added or removed.

**Rationale**: This is the verification step that lets us commit to "no migration needed" with confidence. The grep is exhaustive: any code that touches `"type": "file"` is in the result set. None of those sites depend on a field that's being changed.

**Alternatives considered**: None — this is a verification step, not a design choice.

## R8: How should the test for `test_modifies_link_targets_resolve_to_real_entities` be implemented?

**Decision**: After running the full `run_git_provenance` stage on a fixture workspace, walk every link file in `pkg_root/links/`, parse out the `to_id` for any `modifies`-type link, and assert that an entity file exists at the corresponding sharded path.

**Rationale**:
- This is the highest-level acceptance test for US1. It validates the end-to-end claim of the spec: no `modifies` link is dangling.
- Walking the file system rather than mocking is the right level of integration for a stage test in this codebase (matches the pattern in `tests/test_git_provenance_stage.py`).
- The test stays meaningful even if `build_file_nodes` is later refactored — it asserts the contract, not the implementation.

**Alternatives considered**:
- *Mock the file system and assert calls*: Rejected. The bug being fixed was a file-system-level coupling; mocking would have hidden it for years.
- *Assert the count of file entities equals the count of distinct paths*: Already covered by `test_build_file_nodes_creates_one_entity_per_distinct_path`. Different scope.

## R9: How should the deletion of `text/code` from `PARSER_BY_SUFFIX` affect ingest of code files in non-default configs?

**Decision**: Ingest of code files becomes a no-op skip. Any user with `.py` (or any of the 5 code extensions) in their custom `allowed_extensions` will see the file ingested as `parser_id == "text/unknown"` (the fallback in `parser_id_for`), which then returns `ParseResult(status="skipped", skip_reason="unsupported_extension")` from `parse_file`.

**Rationale**:
- This matches the project's existing behavior for any unknown extension.
- It is a visible behavior change for users who customized `allowed_extensions` to include code files. The CHANGELOG calls this out.
- Removing the entry from `PARSER_BY_SUFFIX` is the correct move because the only consumer (`parse_file`) doesn't handle `text/code` after Phase B's deletion of the branch. Leaving the entry would be misleading.

**Alternatives considered**:
- *Keep `.py` etc. in `PARSER_BY_SUFFIX` as `text/code` but make the parse_file branch a no-op skip*: Rejected. Dead code surface area. The whole point of Phase B is to remove dead code, not relocate it.
- *Rename `text/code` to `text/unsupported` and keep the entries*: Rejected. Confusing for the same reason.

## R10: Should `auditgraph/ingest/policy.py:DEFAULT_ALLOWED_EXTENSIONS` AND `auditgraph/config.py:DEFAULT_CONFIG.allowed_extensions` be deduplicated as part of this work?

**Decision**: No. The duplication exists today and is a separate concern. Update both lists in this spec, leave the deduplication for another spec if anyone cares.

**Rationale**:
- Pre-existing duplication. Not introduced by this change.
- Spec scope discipline: the spec's job is to remove code extraction, not refactor unrelated config-loading concerns.
- Consolidating the two sources of truth would require deciding which one wins, which has its own design discussion. Out of scope here.

**Alternatives considered**:
- *Make `DEFAULT_CONFIG` reference `DEFAULT_ALLOWED_EXTENSIONS` directly*: Plausible, but expands scope. Tracking as a follow-up.
- *Remove `DEFAULT_ALLOWED_EXTENSIONS` from `policy.py`*: Same — out of scope.
