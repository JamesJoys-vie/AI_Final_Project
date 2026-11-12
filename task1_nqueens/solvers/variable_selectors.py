"""Strategies for "which conflicted variable (row) do we repair next?" in Min-Conflicts (Strategy pattern)."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from typing import List, Tuple

Conflicted = List[Tuple[int, int]]


class VariableSelector(ABC):
    name = "Selector"

    def reset(self, n: int) -> None:
        pass

    @abstractmethod
    def select(self, conflicted: Conflicted, rng: random.Random) -> int:
        """`conflicted` = list of (row, number of conflicts) with conflicts > 0. Return the row to repair."""

    def notify_moved(self, row: int) -> None:
        pass


class RandomConflictedSelector(VariableSelector):
    """Standard Min-Conflicts (AIMA / Lecture 08): pick a conflicted variable uniformly at random."""

    name = "Standard (random conflicted)"

    def select(self, conflicted: Conflicted, rng: random.Random) -> int:
        return rng.choice(conflicted)[0]


class MaxConflictTabuSelector(VariableSelector):
    """
    Proposed heuristic: pick the MOST conflicted variable (it removes the most attacks at once),
    ties broken randomly. A short tabu list forbids re-picking a row moved in the last few steps,
    which stops the greedy choice from cycling on the same queen (plateau escape, Lecture 08).
    """

    name = "Heuristic (max-conflict + tabu)"

    def __init__(self, tenure: int = 0):
        self.fixed_tenure = tenure
        self.tabu: deque = deque()

    def reset(self, n: int) -> None:
        tenure = self.fixed_tenure or max(1, min(10, n // 10))
        self.tabu = deque(maxlen=tenure)

    def select(self, conflicted: Conflicted, rng: random.Random) -> int:
        candidates = [item for item in conflicted if item[0] not in self.tabu] or conflicted
        best = max(count for _, count in candidates)
        return rng.choice([row for row, count in candidates if count == best])

    def notify_moved(self, row: int) -> None:
        self.tabu.append(row)
