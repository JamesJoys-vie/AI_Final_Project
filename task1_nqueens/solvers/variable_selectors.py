"""Strategies for "which conflicted variable (row) do we repair next?" in Min-Conflicts (Strategy pattern)."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from task1_nqueens.solvers.min_conflicts import ConflictBoard


class VariableSelector(ABC):
    name = "Selector"

    def reset(self, n: int) -> None:
        pass

    @abstractmethod
    def select(self, board: "ConflictBoard", rng: random.Random) -> int:
        """
        Return the row to repair. The board exposes its incrementally maintained state:
        `board.conflicted` (sorted list of conflicted rows), `board.row_conflicts[row]` and
        `board.buckets` (conflict count -> set of rows). Only called when a conflicted row exists.
        """

    def notify_moved(self, row: int) -> None:
        pass


class RandomConflictedSelector(VariableSelector):
    """Standard Min-Conflicts (AIMA / Lecture 08): pick a conflicted variable uniformly at random."""

    name = "Standard (random conflicted)"

    def select(self, board: "ConflictBoard", rng: random.Random) -> int:
        return rng.choice(board.conflicted)


class MaxConflictTabuSelector(VariableSelector):
    """
    Proposed heuristic: pick the MOST conflicted variable (it removes the most attacks at once),
    ties broken randomly. A short tabu list forbids re-picking a row moved in the last few steps,
    which stops the greedy choice from cycling on the same queen (plateau escape, Lecture 08).
    If every conflicted row is tabu, the tabu list is ignored for that step.
    """

    name = "Heuristic (max-conflict + tabu)"

    def __init__(self, tenure: int = 0):
        self.fixed_tenure = tenure
        self.tabu: deque = deque()
        self.tabu_count: Dict[int, int] = {}  # row -> occurrences in `tabu`, for O(1) membership

    def reset(self, n: int) -> None:
        tenure = self.fixed_tenure or max(1, min(10, n // 10))
        self.tabu = deque(maxlen=tenure)
        self.tabu_count = {}

    def select(self, board: "ConflictBoard", rng: random.Random) -> int:
        # Walk the conflict-count buckets from the highest count down; the first bucket holding
        # a non-tabu row gives the best candidates. Buckets are few (distinct counts), rows per bucket small.
        counts = sorted(board.buckets, reverse=True)
        tabu = self.tabu_count
        for count in counts:
            rows = [row for row in board.buckets[count] if row not in tabu]
            if rows:
                rows.sort()
                return rng.choice(rows)
        return rng.choice(sorted(board.buckets[counts[0]]))

    def notify_moved(self, row: int) -> None:
        if len(self.tabu) == self.tabu.maxlen:
            evicted = self.tabu[0]
            if self.tabu_count[evicted] == 1:
                del self.tabu_count[evicted]
            else:
                self.tabu_count[evicted] -= 1
        self.tabu.append(row)
        self.tabu_count[row] = self.tabu_count.get(row, 0) + 1
