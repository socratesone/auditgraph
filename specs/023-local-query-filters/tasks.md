# Tasks: Local Query Filters & Aggregation

**Input**: Design documents from `/specs/023-local-query-filters/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per user request — TDD approach with explicit test-writing and test-suite-running tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Create new module files and test fixtures

- [x] T001 Create empty module files: `auditgraph/index/type_index.py`, `auditgraph/index/adjacency_builder.py`, `auditgraph/query/filters.py`, `auditgraph/query/list_entities.py`
- [x] T002 [P] Create test fixture directory `tests/fixtures/spec023/` with sample entity JSON files (3+ types: `commit`, `ag:file`, `ner:person`) and sample link JSON files (3+ types: `modifies`, `authored_by`, `CO_OCCURS_WITH`) using the sharded layout
- [x] T003 [P] Create test fixture `tests/fixtures/spec023/config.yaml` with a minimal workspace config for test workspaces

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the per-type indexes, storage loaders, and adjacency rebuild that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] Write tests for `sanitize_type_name` in `tests/test_spec023_type_index.py` — verify `ner:person` -> `ner_person`, `ag:file` -> `ag_file`, `commit` -> `commit`, edge cases (empty string, multiple colons)
- [x] T005 [P] Write tests for `build_type_indexes` in `tests/test_spec023_type_index.py` — verify: creates one file per type at `indexes/types/<sanitized>.json`, each file contains correct entity IDs as JSON array, deterministic output
- [x] T006 [P] Write tests for `build_link_type_indexes` in `tests/test_spec023_type_index.py` — verify: creates one file per link type at `indexes/link-types/<sanitized>.json`, correct link IDs per type
- [x] T007 [P] Write tests for `load_entities_by_type` in `tests/test_spec023_type_index.py` — verify: returns only entities of requested type, returns generator (assert `isinstance(result, types.GeneratorType)`), returns empty iterator for nonexistent type
- [x] T008 [P] Write tests for `load_links` and `load_links_by_type` in `tests/test_spec023_type_index.py` — verify: `load_links` iterates all link files, `load_links_by_type` returns only matching type, both return generators (assert `isinstance(result, types.GeneratorType)`)
- [x] T009 [P] Write tests for `build_adjacency_index` in `tests/test_spec023_adjacency_rebuild.py` — verify: reads all link files (not just co-occurrence), builds correct `{from_id: [{to_id, type, confidence, rule_id}]}` structure, writes to `indexes/graph/adjacency.json`
- [x] T010 Run test suite: `pytest tests/test_spec023_type_index.py tests/test_spec023_adjacency_rebuild.py -v` — confirm all tests FAIL (Red phase)

### Implementation for Foundation

- [x] T011 Implement `sanitize_type_name(type_name: str) -> str` in `auditgraph/index/type_index.py` — replace non-alphanumeric chars with underscores per FR-004
- [x] T012 Implement `build_type_indexes(pkg_root, entities) -> dict[str, Path]` in `auditgraph/index/type_index.py` — group entity IDs by type, write per-type JSON files to `indexes/types/`, return mapping per FR-001
- [x] T013 Implement `build_link_type_indexes(pkg_root) -> dict[str, Path]` in `auditgraph/index/type_index.py` — scan all link files via rglob, group by type, write per-type JSON files to `indexes/link-types/` per FR-002
- [x] T014 [P] Implement `load_entities_by_type(pkg_root, entity_type) -> Iterator[dict]` in `auditgraph/storage/loaders.py` — read type index file, yield entities via `load_entity()` per FR-010, FR-013, FR-014
- [x] T015 [P] Implement `load_links(pkg_root) -> Iterator[dict]` and `load_links_by_type(pkg_root, link_type) -> Iterator[dict]` in `auditgraph/storage/loaders.py` — per FR-011, FR-012, FR-014
- [x] T016 Implement `build_adjacency_index(pkg_root) -> Path` in `auditgraph/index/adjacency_builder.py` — read all links via `load_links()`, build forward adjacency map, write atomically per FR-070
- [x] T017 Wire `build_type_indexes`, `build_link_type_indexes`, and `build_adjacency_index` into `PipelineRunner.run_index()` in `auditgraph/pipeline/runner.py` — call after `build_bm25_index`, update `outputs_hash` per FR-003
- [x] T018 Run test suite: `pytest tests/test_spec023_type_index.py tests/test_spec023_adjacency_rebuild.py -v` — confirm all tests PASS (Green phase)
- [x] T019 Run full existing test suite: `pytest tests/ -v` — confirm no regressions (SC-005)

**Checkpoint**: Type indexes, link-type indexes, storage loaders, and adjacency rebuild all working. All foundation tests green. No regressions.

---

## Phase 3: User Story 1 - Filter Entities by Type (Priority: P1) + User Story 3 - Browse Without Keyword (Priority: P1)

**Goal**: Implement the `list` command with `--type` filtering. US1 and US3 are combined because `list` is the command that enables both — type filtering (US1) and keyword-free browsing (US3).

**Independent Test**: `auditgraph list --type commit` returns only commit entities; `auditgraph list` returns all entities without requiring `--q`.

### Tests for US1+US3

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T020 [P] [US1] Write tests for `list_entities` with `--type` in `tests/test_spec023_list_command.py` — verify: single type returns only matching entities, multiple types OR'd, nonexistent type returns empty, no `--q` required
- [x] T021 [P] [US1] Write tests for `list_entities` with no filters in `tests/test_spec023_list_command.py` — verify: returns all entities (US3 acceptance scenario 1)
- [x] T022 Run test suite: `pytest tests/test_spec023_list_command.py -v` — confirm tests FAIL (Red phase)

### Implementation for US1+US3

- [x] T023 [US1] Implement `list_entities(pkg_root, *, types, ...) -> dict` in `auditgraph/query/list_entities.py` — use `load_entities_by_type` when types provided, `load_entities` otherwise; return response envelope with `results`, `total_count`, `limit`, `offset`, `truncated`
- [x] T024 [US1] Add `list` subcommand in `auditgraph/cli.py` `_build_parser()` — register `--type` (append), `--root`, `--config`; add `if args.command == "list":` dispatch in `main()`
- [x] T025 Run test suite: `pytest tests/test_spec023_list_command.py -v` — confirm all tests PASS (Green phase)
- [x] T026 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph list --type commit` works. `auditgraph list` works without `--q`. US1 and US3 independently testable.

---

## Phase 4: User Story 2 - Filter by Field Predicate (Priority: P1)

**Goal**: Add `--where` field predicates to `list` (and later `query`).

**Independent Test**: `auditgraph list --type commit --where "author_email=alice@example.com"` returns only Alice's commits.

### Tests for US2

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T027 [P] [US2] Write tests for `parse_predicate` in `tests/test_spec023_filters.py` — verify: operator precedence (`>=` before `=`), numeric detection (`0.8` = numeric, `alice@example.com` = string), field/value extraction, edge cases (value containing `=`, empty field)
- [x] T028 [P] [US2] Write tests for `matches` in `tests/test_spec023_filters.py` — verify: all 7 operators on scalar fields, missing field returns False, array field with `=` checks membership, array field with `~` checks substring in any element, array field with `>` returns False, numeric comparison (`mention_count>=5`)
- [x] T029 [P] [US2] Write tests for `apply_filters` in `tests/test_spec023_filters.py` — verify: type filter (OR), predicate filter (AND), combined type+predicate, returns generator
- [x] T030 [P] [US2] Write integration tests for `list_entities` with `--where` in `tests/test_spec023_list_command.py` — verify: single predicate, multiple predicates AND'd, nonexistent field excludes entity
- [x] T031 Run test suite: `pytest tests/test_spec023_filters.py tests/test_spec023_list_command.py -v` — confirm new tests FAIL (Red phase)

### Implementation for US2

- [x] T032 [US2] Implement `FilterPredicate` dataclass and `parse_predicate(expr) -> FilterPredicate` in `auditgraph/query/filters.py` — per FR-025, FR-026
- [x] T033 [US2] Implement `matches(entity, predicate) -> bool` in `auditgraph/query/filters.py` — per FR-027 (array handling), FR-025 (numeric coercion)
- [x] T034 [US2] Implement `apply_filters(entities, *, types, predicates) -> Iterator[dict]` in `auditgraph/query/filters.py` — per FR-020, FR-021
- [x] T035 [US2] Wire `--where` (append) into `list` subcommand in `auditgraph/cli.py` and `list_entities` in `auditgraph/query/list_entities.py`
- [x] T036 Run test suite: `pytest tests/test_spec023_filters.py tests/test_spec023_list_command.py -v` — confirm all tests PASS (Green phase)
- [x] T037 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph list --where "field=value"` works. All predicate operators tested. Array membership works.

---

## Phase 5: User Story 5 - Sort and Paginate (Priority: P1)

**Goal**: Add `--sort`, `--desc`, `--limit`, `--offset` to `list`.

**Independent Test**: `auditgraph list --type commit --sort authored_at --desc --limit 10` returns 10 most recent commits in order.

### Tests for US5

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T038 [P] [US5] Write tests for `apply_sort` in `tests/test_spec023_filters.py` — verify: ascending/descending, stable tiebreaker on `entity.id`, missing fields placed last, deterministic output
- [x] T039 [P] [US5] Write tests for `apply_pagination` in `tests/test_spec023_filters.py` — verify: `limit` slices correctly, `offset` skips correctly, `total_count` reflects pre-limit count (FR-043), `limit=0` returns empty, offset beyond count returns empty
- [x] T040 [P] [US5] Write integration tests for sort+paginate in `tests/test_spec023_list_command.py` — verify: `--sort authored_at --desc --limit 5` returns correct ordered results, `--limit 20 --offset 20` paginates correctly
- [x] T041 Run test suite: `pytest tests/test_spec023_filters.py tests/test_spec023_list_command.py -v -k "sort or pagina"` — confirm new tests FAIL (Red phase)

### Implementation for US5

- [x] T042 [US5] Implement `apply_sort(entities, sort_field, descending) -> list[dict]` in `auditgraph/query/filters.py` — per FR-030, FR-032, FR-033
- [x] T043 [US5] Implement `apply_pagination(entities, limit, offset) -> tuple[list[dict], int]` in `auditgraph/query/filters.py` — per FR-031, FR-043
- [x] T044 [US5] Wire `--sort`, `--desc`, `--limit`, `--offset` into `list` subcommand in `auditgraph/cli.py` and `list_entities` pipeline in `auditgraph/query/list_entities.py`
- [x] T045 Run test suite: `pytest tests/test_spec023_filters.py tests/test_spec023_list_command.py -v` — confirm all tests PASS (Green phase)
- [x] T046 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph list --type commit --sort authored_at --desc --limit 10` works. Pagination works. Deterministic ordering verified.

---

## Phase 6: User Story 4 - Filter Neighbors by Edge Type (Priority: P1)

**Goal**: Add `--edge-type` and `--min-confidence` to `neighbors`.

**Independent Test**: `auditgraph neighbors <commit_id> --edge-type authored_by` returns only `authored_by` edges.

### Tests for US4

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T047 [P] [US4] Write tests for `neighbors` with `--edge-type` in `tests/test_spec023_neighbors_filter.py` — verify: single edge type filters correctly, multiple edge types OR'd, nonexistent type returns empty, depth-2 traversal filters both hops
- [x] T048 [P] [US4] Write tests for `neighbors` with `--min-confidence` in `tests/test_spec023_neighbors_filter.py` — verify: filters edges below threshold, combined with `--edge-type`
- [x] T049 Run test suite: `pytest tests/test_spec023_neighbors_filter.py -v` — confirm tests FAIL (Red phase)

### Implementation for US4

- [x] T050 [US4] Modify `neighbors(pkg_root, entity_id, depth, *, edge_types, min_confidence)` in `auditgraph/query/neighbors.py` — filter adjacency edges by type (OR) and confidence before traversal per FR-022, FR-023
- [x] T051 [US4] Wire `--edge-type` (append) and `--min-confidence` (float) into `neighbors` subcommand in `auditgraph/cli.py`
- [x] T052 Run test suite: `pytest tests/test_spec023_neighbors_filter.py -v` — confirm all tests PASS (Green phase)
- [x] T053 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph neighbors <id> --edge-type authored_by` works. Confidence filtering works. No regressions.

---

## Phase 7: User Story 6 - Aggregation (Priority: P2)

**Goal**: Add `--count` and `--group-by` to `list`.

**Independent Test**: `auditgraph list --group-by type --count` returns JSON with per-type counts summing to total.

### Tests for US6

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T054 [P] [US6] Write tests for `apply_aggregation` in `tests/test_spec023_aggregation.py` — verify: `count_only=True` returns `{"count": N}`, `group_by="type"` returns `{"groups": {...}}`, null key for missing group-by field, `--count --limit 5` returns total > 5 when more matches exist (FR-043)
- [x] T055 [P] [US6] Write integration tests for count/group-by in `tests/test_spec023_aggregation.py` — verify: `--count` with `--type`, `--group-by type --count`, `--type commit --group-by author_email --count`
- [x] T056 Run test suite: `pytest tests/test_spec023_aggregation.py -v` — confirm tests FAIL (Red phase)

### Implementation for US6

- [x] T057 [US6] Implement `apply_aggregation(entities, *, count_only, group_by) -> dict` in `auditgraph/query/filters.py` — per FR-040, FR-041, FR-042
- [x] T058 [US6] Wire `--count` (flag) and `--group-by` (string) into `list` subcommand in `auditgraph/cli.py` and `list_entities` pipeline in `auditgraph/query/list_entities.py`
- [x] T059 Run test suite: `pytest tests/test_spec023_aggregation.py -v` — confirm all tests PASS (Green phase)
- [x] T060 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph list --group-by type --count` works. Count/group-by aggregation verified.

---

## Phase 8: User Story 3b + US1b - Extended Query Command (Priority: P1)

**Goal**: Add filter/sort/limit/aggregation params to the existing `query` command (BM25 search + filters).

**Independent Test**: `auditgraph query --q "config" --type ag:file --limit 5` returns at most 5 file entities matching "config".

### Tests for Extended Query

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T061 [P] [US3] Write tests for extended `keyword_search` in `tests/test_spec023_query_extended.py` — verify: `--type` filters BM25 results, `--where` applies to BM25 results, `--sort` + `--limit` work, `--count` works, backwards compatibility (no new params = identical output)
- [x] T062 Run test suite: `pytest tests/test_spec023_query_extended.py -v` — confirm tests FAIL (Red phase)

### Implementation for Extended Query

- [x] T063 [US3] Modify `keyword_search` in `auditgraph/query/keyword.py` to accept optional `types`, `where`, `sort`, `descending`, `limit`, `offset`, `count_only`, `group_by` params — apply filter engine to BM25 results per FR-051
- [x] T064 [US3] Wire `--type`, `--where`, `--sort`, `--desc`, `--limit`, `--offset`, `--count`, `--group-by` into `query` subcommand in `auditgraph/cli.py`
- [x] T065 Run test suite: `pytest tests/test_spec023_query_extended.py -v` — confirm all tests PASS (Green phase)
- [x] T066 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: `auditgraph query --q "term" --type X --sort Y --limit N` works. Backwards compatible.

---

## Phase 9: User Story 7 - MCP Integration (Priority: P1)

**Goal**: Expose all filter/sort/limit/aggregation features via MCP tools.

**Independent Test**: `ag_list(type="commit", limit=10)` via MCP returns at most 10 commits with `total_count` metadata.

### Tests for US7

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T067 [P] [US7] Write tests for `ag_list` MCP tool in `tests/test_spec023_mcp_tools.py` — verify: `type` param filters, `sort`+`limit` work, default limit 100, response envelope has `total_count`/`truncated`/`limit`/`offset`, `count`+`group_by` work
- [x] T068 [P] [US7] Write tests for extended `ag_query` and `ag_neighbors` MCP tools in `tests/test_spec023_mcp_tools.py` — verify: new params accepted, backwards compatible
- [x] T069 Run test suite: `pytest tests/test_spec023_mcp_tools.py -v` — confirm tests FAIL (Red phase)

### Implementation for US7

- [x] T070 [US7] Add `ag_list` tool entry to `llm-tooling/tool.manifest.json` — per contracts/cli-contract.yaml; set `"risk": "low"`, `"idempotency": "idempotent"`, `"command": "list"`, default limit 100 in schema
- [x] T071 [US7] Extend `ag_query` schema in `llm-tooling/tool.manifest.json` — add optional `type`, `where`, `sort`, `limit`, `offset` properties per FR-061
- [x] T072 [US7] Extend `ag_neighbors` schema in `llm-tooling/tool.manifest.json` — add optional `edge_type`, `min_confidence` properties per FR-062
- [x] T073 [US7] Add `"list"` to `ALL_TOOLS` in `auditgraph/utils/mcp_inventory.py`
- [x] T074 [US7] Verify `list` command works via MCP subprocess dispatch in `llm-tooling/mcp/adapters/project.py` — no positional arg handling needed (`list` uses only flags); confirm `build_command("list", {...})` produces correct argv
- [x] T075 Run test suite: `pytest tests/test_spec023_mcp_tools.py -v` — confirm all tests PASS (Green phase)
- [x] T076 Run full test suite: `pytest tests/ -v` — confirm no regressions

**Checkpoint**: All MCP tools working with new parameters. Default limit 100. Response envelope verified.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, edge cases, and cleanup

- [x] T077 [P] Write edge case tests in `tests/test_spec023_filters.py` — empty workspace, `--limit 0`, `--offset` beyond count, case sensitivity for `--type` and `--where`, `--where` on array field with comparison operator
- [x] T078 Run edge case tests: `pytest tests/test_spec023_filters.py -v -k "edge"` — confirm PASS
- [x] T079 Run complete spec 023 test suite: `pytest tests/test_spec023_*.py -v` — confirm ALL green
- [x] T080 Run full project test suite: `pytest tests/ -v` — confirm ZERO regressions across all specs
- [x] T081 Validate quickstart.md scenarios manually — run each example command from `specs/023-local-query-filters/quickstart.md` against a populated workspace

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundation)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1+US3 List)**: Depends on Phase 2
- **Phase 4 (US2 Predicates)**: Depends on Phase 3 (needs `list` command)
- **Phase 5 (US5 Sort/Paginate)**: Depends on Phase 3 (needs `list` command)
- **Phase 6 (US4 Neighbors)**: Depends on Phase 2 (needs adjacency rebuild); can run parallel with Phases 3-5
- **Phase 7 (US6 Aggregation)**: Depends on Phase 3 (needs `list` command)
- **Phase 8 (Extended Query)**: Depends on Phase 4+5 (needs filter engine complete)
- **Phase 9 (US7 MCP)**: Depends on Phases 3-8 (needs all CLI commands working)
- **Phase 10 (Polish)**: Depends on all prior phases

### Parallel Opportunities

```
Phase 2: T004-T009 can all run in parallel (test writing)
Phase 2: T014+T015 can run in parallel (different files)
Phase 4 (US2): T027-T030 can all run in parallel (test writing)
Phase 5 (US5): T038-T040 can all run in parallel (test writing)
Phase 6 (US4): Can run in parallel with Phases 4, 5, 7 (different files)
Phase 9 (US7): T070-T074 can all run in parallel (different files)
```

---

## Implementation Strategy

### MVP First (Phases 1-3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundation (indexes + loaders + adjacency)
3. Complete Phase 3: US1+US3 (list command with type filter)
4. **STOP and VALIDATE**: `auditgraph list --type commit` works
5. This is a usable increment — type-filtered browsing without keywords

### Incremental Delivery

1. Setup + Foundation → indexes and loaders working
2. Add list + type filter (US1+US3) → MVP browsing
3. Add predicates (US2) → field-level filtering
4. Add sort/paginate (US5) → usable for large result sets
5. Add neighbors filter (US4) → graph traversal filtering
6. Add aggregation (US6) → corpus analysis
7. Add extended query (US3b) → search + filter combined
8. Add MCP (US7) → LLM integration ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD is strictly enforced: every phase has explicit "write tests → confirm FAIL → implement → confirm PASS → run full suite" steps
- Full test suite (`pytest tests/ -v`) is run after EVERY phase to catch regressions early
- Commit after each phase checkpoint
