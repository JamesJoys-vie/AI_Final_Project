"""
Pre-computed table of digit sets: all sets of k distinct digits (1..9) whose sum is s.
Example: (2 cells, sum 16) -> {7, 9} only, so both cells get domain {7, 9} before any search.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from typing import FrozenSet, Tuple


@lru_cache(maxsize=None)
def digit_sets(length: int, total: int) -> Tuple[FrozenSet[int], ...]:
    return tuple(frozenset(combo) for combo in combinations(range(1, 10), length) if sum(combo) == total)


@lru_cache(maxsize=None)
def possible_digits(length: int, total: int) -> FrozenSet[int]:
    """Union of all valid digit sets: the tightest domain a cell can have from this run alone."""
    result: FrozenSet[int] = frozenset()
    for digits in digit_sets(length, total):
        result |= digits
    return result
