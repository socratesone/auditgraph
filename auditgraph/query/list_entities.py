"""List entities with filtering, sorting, pagination, and aggregation."""
from __future__ import annotations

from pathlib import Path

from auditgraph.query.filters import (
    apply_aggregation,
    apply_filters,
    apply_pagination,
    apply_sort,
    parse_predicate,
)
from auditgraph.storage.loaders import load_entities, load_entities_by_type


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
    """Query entities with optional type filter, predicates, sort, and pagination."""
    # Load entities
    if types:
        entities: list[dict[str, object]] = []
        for t in types:
            entities.extend(load_entities_by_type(pkg_root, t))
    else:
        entities = load_entities(pkg_root)

    # Apply predicate filters
    predicates = [parse_predicate(w) for w in where] if where else None
    filtered = list(apply_filters(entities, predicates=predicates))

    # Aggregation short-circuit
    agg = apply_aggregation(filtered, count_only=count_only, group_by=group_by)
    if agg is not None:
        return agg

    # Sort
    sorted_entities = apply_sort(filtered, sort_field=sort, descending=descending)

    # Pagination
    results, total_count = apply_pagination(sorted_entities, limit=limit, offset=offset)
    truncated = limit is not None and total_count > (offset + limit)

    return {
        "results": results,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "truncated": truncated,
    }
