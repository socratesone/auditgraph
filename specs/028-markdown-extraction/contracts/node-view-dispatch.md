# Contract: `node_view` ID-prefix dispatch

**Module**: `auditgraph/query/node_view.py`
**Consumers**: `auditgraph/cli.py` (via `node_parser` handler), `llm-tooling/` MCP tools (indirect via `ag_node` if present).

## Public signature (unchanged)

```python
def node_view(pkg_root: Path, entity_id: str) -> dict[str, object]:
    ...
```

Signature is preserved for backward compatibility. Only internal dispatch logic changes.

## New behavior

Dispatch is table-driven by ID prefix:

```python
_DISPATCH: list[tuple[str, Callable[[Path, str], dict[str, object] | None]]] = [
    ("doc_",  _resolve_document),
    ("chk_",  _resolve_chunk),
    # Everything else (ent_, commit_, tag_, ref_, author_, file_, repo_, note_)
    # falls through to _resolve_entity.
]

def node_view(pkg_root: Path, entity_id: str) -> dict[str, object]:
    for prefix, resolver in _DISPATCH:
        if entity_id.startswith(prefix):
            view = resolver(pkg_root, entity_id)
            if view is not None:
                return view
            break  # preferred location didn't have it; try fall-through
    # Fall-through: try every resolver + generic entity
    for prefix, resolver in _DISPATCH:
        view = resolver(pkg_root, entity_id)
        if view is not None:
            return view
    view = _resolve_entity(pkg_root, entity_id)
    if view is not None:
        return view
    return {
        "status": "error",
        "code": "not_found",
        "message": f"No node found for id '{entity_id}' in documents/, chunks/, or entities/.",
    }
```

## Resolver contracts

Each resolver returns either a valid view dict or `None` (miss). Never raises `FileNotFoundError` to the caller — the top-level function is responsible for the not-found error envelope.

### `_resolve_document(pkg_root, doc_id)`

- Looks at `pkg_root / "documents" / f"{doc_id}.json"`.
- If file exists, returns:

  ```json
  {
    "id": "<document_id>",
    "type": "document",
    "name": "<source_path basename or title>",
    "source_path": "...",
    "source_hash": "...",
    "mime_type": "...",
    "refs": []
  }
  ```

- Field names align with the existing document artifact schema from `auditgraph/storage/artifacts.py :: write_document_artifacts`.

### `_resolve_chunk(pkg_root, chunk_id)`

- Preserves the existing `rglob` behavior from the current `node_view.py:11-28`.
- Returns the same view shape as today (chunk_id, text, citation, refs).

### `_resolve_entity(pkg_root, entity_id)`

- Calls existing `load_entity(pkg_root, entity_id)` (unchanged).
- Wraps a `FileNotFoundError` into `None` return.
- Returns the existing entity view shape (id, type, name, refs).

## Error envelope

Missing IDs return a structured error dict:

```json
{ "status": "error", "code": "not_found", "message": "..." }
```

- `code` is a stable identifier for machine consumers.
- `message` is human-friendly and lists the subtrees searched. It does NOT surface OS-level errors (no more `[Errno 2] No such file or directory: '.../entities/81/doc_...'`).

## Test contract

- **Document resolves**: materialize a `documents/<doc_id>.json`, call `node_view`, assert returns the document view.
- **Chunk resolves**: materialize a `chunks/<shard>/<chk_id>.json`, call `node_view`, assert returns the chunk view.
- **Entity resolves**: materialize an `entities/<shard>/<ent_id>.json`, call `node_view`, assert returns the entity view.
- **Git-provenance entity resolves**: materialize a `commit_<id>.json` under `entities/<shard>/` (existing git materializer convention), assert `node_view` returns it correctly (the fall-through is exercised).
- **Unknown ID**: call `node_view(pkg_root, "doc_deadbeef")` with no such file; assert returned dict has `status == "error"`, `code == "not_found"`.
- **Prefix-wrong-location fall-through**: hand-craft a scenario where a `doc_…` ID file happens to live under `entities/<shard>/` (pathological but defensive); assert the fall-through still resolves it.
