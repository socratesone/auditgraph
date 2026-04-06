"""Predicate parser, filter engine, sort, pagination, and aggregation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator


@dataclass
class FilterPredicate:
    """A parsed field predicate."""

    field: str
    operator: str  # =, !=, >, >=, <, <=, ~
    value: str
    is_numeric: bool


# Regex for numeric values (int or float, optionally negative)
_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")

# Operators ordered by length (longest first so >= is matched before >)
_OPERATORS = [">=", "<=", "!=", ">", "<", "~", "="]


def parse_predicate(expr: str) -> FilterPredicate:
    """Parse 'field<op>value' into a FilterPredicate."""
    for op in _OPERATORS:
        idx = expr.find(op)
        if idx > 0:
            field = expr[:idx]
            value = expr[idx + len(op) :]
            is_numeric = bool(_NUMERIC_RE.match(value))
            return FilterPredicate(field=field, operator=op, value=value, is_numeric=is_numeric)
    raise ValueError(f"Cannot parse predicate: {expr!r}")


def matches(entity: dict, predicate: FilterPredicate) -> bool:
    """Test whether *entity* satisfies *predicate*."""
    field_val = entity.get(predicate.field)
    if field_val is None:
        return False

    op = predicate.operator

    # Array fields: membership / substring semantics
    if isinstance(field_val, list):
        if op == "=":
            return predicate.value in field_val
        if op == "!=":
            return predicate.value not in field_val
        if op == "~":
            return any(predicate.value in str(item) for item in field_val)
        # Comparisons (>, >=, <, <=) are not meaningful on arrays
        return False

    # Boolean coercion
    if isinstance(field_val, bool):
        bool_val = predicate.value.lower() in ("true", "1", "yes")
        if op == "=":
            return field_val is bool_val
        if op == "!=":
            return field_val is not bool_val
        return False

    # Numeric comparison
    if predicate.is_numeric:
        try:
            num_field = float(field_val)
            num_pred = float(predicate.value)
        except (TypeError, ValueError):
            return False
        if op == "=":
            return num_field == num_pred
        if op == "!=":
            return num_field != num_pred
        if op == ">":
            return num_field > num_pred
        if op == ">=":
            return num_field >= num_pred
        if op == "<":
            return num_field < num_pred
        if op == "<=":
            return num_field <= num_pred
        return False

    # String comparison
    str_val = str(field_val)
    if op == "=":
        return str_val == predicate.value
    if op == "!=":
        return str_val != predicate.value
    if op == "~":
        return predicate.value in str_val
    if op == ">":
        return str_val > predicate.value
    if op == ">=":
        return str_val >= predicate.value
    if op == "<":
        return str_val < predicate.value
    if op == "<=":
        return str_val <= predicate.value
    return False


def _sort_key(entity: dict, sort_field: str | None) -> tuple:
    """Build a sort key tuple: (has_value, field_value, id).

    Missing fields sort last by using (1, ...) vs (0, ...).
    """
    entity_id = str(entity.get("id", ""))
    if sort_field is None:
        return (0, "", entity_id)
    val = entity.get(sort_field)
    if val is None:
        return (1, "", entity_id)  # missing → last
    # Try numeric comparison
    try:
        num = float(val)
        return (0, num, entity_id)
    except (TypeError, ValueError):
        return (0, str(val), entity_id)


def apply_sort(
    entities: list[dict[str, object]],
    sort_field: str | None = None,
    descending: bool = False,
) -> list[dict[str, object]]:
    """Sort entities by field with ID tiebreaker. Missing fields sort last."""
    if sort_field is None:
        # Default: sort by id ascending
        return sorted(entities, key=lambda e: str(e.get("id", "")))

    def key_func(entity: dict) -> tuple:
        return _sort_key(entity, sort_field)

    # Sort ascending first, then reverse the non-missing portion if descending
    if not descending:
        return sorted(entities, key=key_func)

    # For descending: entities with values should be reversed, missing still last
    has_val = []
    missing = []
    for e in entities:
        if e.get(sort_field) is None:
            missing.append(e)
        else:
            has_val.append(e)
    has_val_sorted = sorted(has_val, key=key_func, reverse=True)
    missing_sorted = sorted(missing, key=lambda e: str(e.get("id", "")))
    return has_val_sorted + missing_sorted


def apply_pagination(
    entities: list[dict[str, object]],
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    """Paginate entities. Returns (page_results, total_count_pre_pagination)."""
    total = len(entities)
    if limit is not None:
        return entities[offset : offset + limit], total
    return entities[offset:], total


def apply_aggregation(
    entities: list[dict[str, object]],
    count_only: bool = False,
    group_by: str | None = None,
) -> dict[str, object] | None:
    """Apply aggregation to entities. Returns dict or None if no aggregation requested."""
    if group_by:
        groups: dict[str, int] = {}
        for entity in entities:
            key = entity.get(group_by)
            if key is None:
                group_key = "_missing"
            else:
                group_key = str(key)
            groups[group_key] = groups.get(group_key, 0) + 1
        return {"groups": groups, "total_count": len(entities)}
    if count_only:
        return {"count": len(entities)}
    return None


def apply_filters(
    entities: list[dict[str, object]] | Iterator[dict[str, object]],
    *,
    types: list[str] | None = None,
    predicates: list[FilterPredicate] | None = None,
) -> Iterator[dict[str, object]]:
    """Yield entities matching all type and predicate filters."""
    type_set = set(types) if types else None
    for entity in entities:
        if type_set and entity.get("type") not in type_set:
            continue
        if predicates:
            if not all(matches(entity, p) for p in predicates):
                continue
        yield entity
