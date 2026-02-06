from __future__ import annotations

from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


def stable_sorted(items: Iterable[T], key: Callable[[T], tuple]) -> list[T]:
    return sorted(items, key=key)
