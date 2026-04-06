# Implementation Plan: Local Query Filters & Aggregation

**Branch**: `023-local-query-filters` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-local-query-filters/spec.md`

## Summary

Add deterministic filtering, sorting, pagination, and aggregation primitives to auditgraph's local query layer. The approach is layered: new per-type indexes enable selective entity/link loading, a reusable filter engine parses predicates and applies them in memory, and the CLI and MCP interfaces expose the new parameters additively. A prerequisite fix rebuilds the forward adjacency index to include git-provenance links (currently missing).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PyYAML (config), argparse (CLI), json (storage/I/O)
**Storage**: Sharded JSON files under `.pkg/profiles/<profile>/` — entities (123K+), links (1.5M+), indexes (BM25, adjacency)
**Testing**: pytest with `--strict-markers`, flat test directory, fixtures in `tests/fixtures/`
**Target Platform**: Linux (x86_64), macOS (Intel/Apple Silicon), CLI-only
**Project Type**: Single Python package (`auditgraph/`)
**Performance Goals**: Type-filtered queries over 123K entities in ≤ 2 seconds
**Constraints**: Local-first (no network), deterministic output, backwards-compatible CLI/MCP
**Scale/Scope**: Default profile: 123K entities, 1.5M links, 13 entity types, 7 link types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| DRY — Single source of truth | PASS | Filter engine is a single shared module; CLI and MCP both route through it |
| SOLID — Single Responsibility | PASS | Separate modules: index builders, storage loaders, filter engine, CLI wiring, MCP adapter |
| SOLID — Open/Closed | PASS | New index types plug into `run_index` alongside BM25; filter engine is composable |
| SOLID — Dependency Inversion | PASS | Query functions depend on `pkg_root: Path` abstraction, not concrete file layout |
| TDD — Tests first | PASS | Task ordering: tests written before implementation for each layer |
| Simplicity — YAGNI | PASS | No speculative features; flat fields only, no query DSL, no reverse adjacency |
| Determinism | PASS | Stable sort with ID tiebreaker; index rebuild is deterministic |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/023-local-query-filters/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
auditgraph/
├── index/
│   ├── bm25.py              # Existing — BM25 inverted index builder
│   ├── type_index.py         # NEW — per-type entity/link index builder
│   └── adjacency_builder.py  # NEW — forward adjacency rebuild (fix for FR-070)
├── storage/
│   └── loaders.py            # MODIFY — add load_entities_by_type, load_links, load_links_by_type
├── query/
│   ├── keyword.py            # MODIFY — add filter/sort/limit/aggregation params
│   ├── neighbors.py          # MODIFY — add edge_type, min_confidence params
│   ├── list_entities.py      # NEW — list command implementation
│   └── filters.py            # NEW — predicate parser, filter engine, sort, pagination, aggregation
├── cli.py                    # MODIFY — add 'list' subcommand, extend 'query' and 'neighbors' args
├── pipeline/
│   └── runner.py             # MODIFY — wire type_index and adjacency_builder into run_index
└── utils/
    └── mcp_inventory.py      # MODIFY — add 'list' to ALL_TOOLS

llm-tooling/
├── tool.manifest.json        # MODIFY — add ag_list tool, extend ag_query and ag_neighbors schemas
└── mcp/
    └── adapters/
        └── project.py        # MODIFY — add 'list' to _apply_positional if needed

tests/
├── test_spec023_type_index.py        # NEW — index builder tests
├── test_spec023_filters.py           # NEW — filter engine unit tests
├── test_spec023_list_command.py      # NEW — list CLI integration tests
├── test_spec023_query_extended.py    # NEW — extended query tests
├── test_spec023_neighbors_filter.py  # NEW — neighbors edge-type filter tests
├── test_spec023_aggregation.py       # NEW — count/group-by tests
├── test_spec023_mcp_tools.py         # NEW — MCP tool integration tests
└── test_spec023_adjacency_rebuild.py # NEW — adjacency rebuild tests
```

**Structure Decision**: All new modules follow existing patterns — query functions in `auditgraph/query/`, index builders in `auditgraph/index/`, storage loaders in `auditgraph/storage/loaders.py`. No new packages needed. Tests follow the `test_spec<NNN>_<topic>.py` convention.

## Implementation Phases

### Phase 1: Indexes & Storage (Foundation)

**Goal**: Build the per-type indexes and selective loaders that all query features depend on.

#### 1A: Type Index Builder (`auditgraph/index/type_index.py`)

New module with two functions:

```python
def sanitize_type_name(type_name: str) -> str:
    """Replace non-alphanumeric characters with underscores."""

def build_type_indexes(pkg_root: Path, entities: Iterable[dict]) -> dict[str, Path]:
    """Build per-type entity index files.
    
    Writes: indexes/types/<sanitized_type>.json (one per type)
    Each file: JSON array of entity IDs for that type.
    Returns: mapping of type_name -> written file path.
    """

def build_link_type_indexes(pkg_root: Path) -> dict[str, Path]:
    """Build per-type link index files.
    
    Reads all link files via rglob.
    Writes: indexes/link-types/<sanitized_type>.json
    Returns: mapping of link_type -> written file path.
    """
```

Wire into `PipelineRunner.run_index()` after `build_bm25_index`. Update `outputs_hash` to include type index paths.

#### 1B: Storage Loaders (`auditgraph/storage/loaders.py`)

Add three new functions alongside existing `load_entity` and `load_entities`:

```python
def load_entities_by_type(pkg_root: Path, entity_type: str) -> Iterator[dict]:
    """Load entities of a specific type using the type index.
    
    Reads indexes/types/<sanitized_type>.json for the ID list,
    then loads each entity via load_entity().
    Yields dicts (generator, not list).
    """

def load_links(pkg_root: Path) -> Iterator[dict]:
    """Iterate all link files. Generator over rglob('lnk_*.json')."""

def load_links_by_type(pkg_root: Path, link_type: str) -> Iterator[dict]:
    """Load links of a specific type using the link-type index.
    
    Reads indexes/link-types/<sanitized_type>.json for the ID list,
    then loads each link file.
    Yields dicts.
    """
```

#### 1C: Adjacency Rebuild Fix (`auditgraph/index/adjacency_builder.py`)

New module that rebuilds the forward adjacency index from **all** link files (not just co-occurrence links):

```python
def build_adjacency_index(pkg_root: Path) -> Path:
    """Rebuild indexes/graph/adjacency.json from all link files.
    
    Reads all links via load_links().
    Builds: {from_id: [{to_id, type, confidence, rule_id}, ...]}.
    Writes atomically. Returns path.
    """
```

Wire into `run_index` after type indexes. This fixes FR-070 — the adjacency index will now include git-provenance links.

### Phase 2: Filter Engine (`auditgraph/query/filters.py`)

**Goal**: Reusable predicate parsing, filtering, sorting, pagination, and aggregation.

```python
@dataclass
class FilterPredicate:
    field: str
    operator: str    # =, !=, >, >=, <, <=, ~
    value: str
    is_numeric: bool

def parse_predicate(expr: str) -> FilterPredicate:
    """Parse 'field<op>value' string.
    
    Operator precedence: >=, <=, != first, then >, <, =, ~.
    Numeric detection: value matches ^-?\d+(\.\d+)?$.
    """

def matches(entity: dict, predicate: FilterPredicate) -> bool:
    """Test if entity matches a single predicate.
    
    Missing field -> False.
    Array field + '=' -> membership check.
    Array field + '~' -> any element contains substring.
    Array field + comparison op -> False (treated as missing).
    Numeric values compared as float; strings compared lexicographically.
    """

def apply_filters(
    entities: Iterable[dict],
    *,
    types: list[str] | None = None,
    predicates: list[FilterPredicate] | None = None,
) -> Iterator[dict]:
    """Filter entities by type (OR) and predicates (AND). Generator."""

def apply_sort(
    entities: list[dict],
    sort_field: str | None = None,
    descending: bool = False,
) -> list[dict]:
    """Sort with stable tiebreaker on entity['id']. Missing fields last."""

def apply_pagination(
    entities: list[dict],
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Apply offset/limit. Returns (page, total_count)."""

def apply_aggregation(
    entities: Iterable[dict],
    *,
    count_only: bool = False,
    group_by: str | None = None,
) -> dict:
    """Aggregate entities. Returns {"count": N} or {"groups": {...}}."""
```

### Phase 3: CLI Integration

#### 3A: List Command (`auditgraph/query/list_entities.py`)

```python
def list_entities(
    pkg_root: Path,
    *,
    types: list[str] | None = None,
    where: list[str] | None = None,
    sort: str | None = None,
    descending: bool = False,
    limit: int | None = None,
    offset: int = 0,
    count_only: bool = False,
    group_by: str | None = None,
) -> dict[str, object]:
    """List entities with filtering, sorting, pagination, aggregation.
    
    Uses load_entities_by_type when types specified, else load_entities.
    Applies filter engine pipeline: filter -> sort -> paginate/aggregate.
    Returns response with results, total_count, limit, offset, truncated.
    """
```

#### 3B: CLI Wiring (`auditgraph/cli.py`)

Add `list` subcommand in `_build_parser()`:
```
--type (multiple, action=append)
--where (multiple, action=append)
--sort (single)
--desc (flag)
--limit (int)
--offset (int, default=0)
--count (flag)
--group-by (single)
--root, --config (standard)
```

Extend `query` subcommand with same params (except `--q` remains required).
Extend `neighbors` subcommand with `--edge-type` (multiple) and `--min-confidence` (float).

#### 3C: Extended Query (`auditgraph/query/keyword.py`)

Modify `keyword_search` to accept optional filter/sort/limit params. Apply filter engine to BM25 results before returning.

#### 3D: Extended Neighbors (`auditgraph/query/neighbors.py`)

Modify `neighbors` to accept optional `edge_types: list[str]` and `min_confidence: float`. Filter adjacency edges before traversal.

### Phase 4: MCP Integration

#### 4A: Tool Manifest (`llm-tooling/tool.manifest.json`)

Add `ag_list` tool entry. Extend `ag_query` and `ag_neighbors` schemas with new optional properties.

#### 4B: MCP Inventory (`auditgraph/utils/mcp_inventory.py`)

Add `"list"` to `ALL_TOOLS`.

#### 4C: Response Envelope

The `list_entities` function returns the envelope format directly:
```json
{"results": [...], "total_count": N, "limit": N, "offset": N, "truncated": bool}
```

MCP default limit (100) is applied in the MCP adapter or CLI dispatch when the caller is MCP (detected via command context).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Adjacency rebuild too slow (1.5M links) | Medium | Medium | Stream via generator; benchmark during Phase 1 |
| Type index stale after manual entity edits | Low | Low | Document: re-run `auditgraph index` after edits |
| `--where` parser ambiguity with edge cases | Low | Medium | Comprehensive unit tests for parser in Phase 2 |
| MCP default limit surprises users | Low | Low | `truncated: true` + `total_count` make it transparent |

## Dependencies

```
Phase 1 (Indexes/Storage) ← no dependencies
Phase 2 (Filter Engine) ← Phase 1 (needs loaders)
Phase 3 (CLI) ← Phase 2 (needs filter engine) + Phase 1 (needs adjacency fix for neighbors)
Phase 4 (MCP) ← Phase 3 (needs CLI commands working)
```

All phases are strictly sequential within each layer, but tests can be written in parallel with implementation (TDD).
