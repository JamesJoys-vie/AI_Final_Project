"""Min-Conflicts local search for N-Queens (Lecture 08) with pluggable variable-selection heuristics.

CSP view : variable = column c, value = row of its queen -> queens[c] in {0..N-1}
           (the 'one queen per column' constraint is built into the representation).
Conflict : number of OTHER queens attacking the queen of column c (same row / diagonal).
Everything is O(1) per queen thanks to counters on rows and the two diagonal families.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .board import Board


class ConflictState:
    """Assignment + incremental counters (rows, r-c diagonals, r+c diagonals)."""

    def __init__(self, n: int, queens: np.ndarray):
        self.n = n
        self.cols = np.arange(n)
        self.queens = np.asarray(queens, dtype=np.int64).copy()
        q, c = self.queens, self.cols
        self.row_cnt = np.bincount(q, minlength=n)
        self.d1_cnt = np.bincount(q - c + n - 1, minlength=2 * n - 1)  # main diagonals (r - c)
        self.d2_cnt = np.bincount(q + c, minlength=2 * n - 1)          # anti diagonals (r + c)

    def all_conflicts(self) -> np.ndarray:
        """conflicts[c] = number of queens attacking queen at column c (vectorized O(N))."""
        q, c, n = self.queens, self.cols, self.n
        return self.row_cnt[q] + self.d1_cnt[q - c + n - 1] + self.d2_cnt[q + c] - 3

    def row_costs(self, col: int) -> np.ndarray:
        """costs[r] = conflicts the queen of `col` would have if placed at row r."""
        n, rows = self.n, self.cols
        costs = self.row_cnt + self.d1_cnt[rows - col + n - 1] + self.d2_cnt[rows + col]
        costs[self.queens[col]] -= 3  # subtract self contribution
        return costs

    def move(self, col: int, new_row: int) -> None:
        old, n = self.queens[col], self.n
        if old == new_row:
            return
        self.row_cnt[old] -= 1
        self.d1_cnt[old - col + n - 1] -= 1
        self.d2_cnt[old + col] -= 1
        self.queens[col] = new_row
        self.row_cnt[new_row] += 1
        self.d1_cnt[new_row - col + n - 1] += 1
        self.d2_cnt[new_row + col] += 1


# --------------------------------------------------------------------------- selectors
class VariableSelector(ABC):
    """Strategy interface: which conflicted variable (column) do we repair next?"""

    name = "base"

    @abstractmethod
    def select(self, conflicts: np.ndarray, conflicted: np.ndarray,
               rng: np.random.Generator, last_moved: Optional[int]) -> int: ...


class RandomConflictedSelector(VariableSelector):
    """STANDARD Min-Conflicts: uniformly random variable among the conflicted ones."""

    name = "standard"

    def select(self, conflicts, conflicted, rng, last_moved):
        return int(rng.choice(conflicted))


class MaxConflictSelector(VariableSelector):
    """PROPOSED heuristic (most-constrained-first with noise and 1-step tabu).

    1. With probability `noise`, pick a random conflicted variable (escapes plateaus).
    2. Otherwise pick the variable with the MAXIMUM conflicts (worst offender first).
    3. The variable moved in the previous step is excluded (1-step tabu) when candidates > 1.
    Ties are broken uniformly at random.
    """

    name = "max_conflict"

    def __init__(self, noise: float = 0.05, use_tabu: bool = True):
        self.noise = noise
        self.use_tabu = use_tabu

    def select(self, conflicts, conflicted, rng, last_moved):
        if rng.random() < self.noise:
            return int(rng.choice(conflicted))
        cand = conflicted
        if self.use_tabu and last_moved is not None and cand.size > 1:
            cand = cand[cand != last_moved]
        values = conflicts[cand]
        return int(rng.choice(cand[values == values.max()]))


# --------------------------------------------------------------------------- solver
@dataclass
class MinConflictsResult:
    n: int
    strategy: str
    seed: Optional[int]
    solved: bool
    steps: int
    time: float
    board: Board
    history: List[int] = field(default_factory=list)


class MinConflictsSolver:
    def __init__(self, selector: Optional[VariableSelector] = None, max_steps: int = 100_000):
        self.selector = selector or RandomConflictedSelector()
        self.max_steps = max_steps

    def solve(self, n: int, seed: Optional[int] = None, record_history: bool = False) -> MinConflictsResult:
        if n < 1:
            raise ValueError("N must be >= 1")
        if n in (2, 3):
            raise ValueError("N-Queens has no solution for N = 2 or 3")

        rng = np.random.default_rng(seed)
        # Random initial configuration: one queen per column
        state = ConflictState(n, rng.integers(0, n, size=n))
        history: List[int] = []
        last_moved: Optional[int] = None
        solved, steps = False, 0

        t0 = time.perf_counter()
        for steps in range(self.max_steps + 1):
            conflicts = state.all_conflicts()
            conflicted = np.flatnonzero(conflicts > 0)
            if record_history:
                history.append(int(conflicted.size))
            if conflicted.size == 0:
                solved = True
                break
            if steps == self.max_steps:
                break

            # 1. Select variable
            col = self.selector.select(conflicts, conflicted, rng, last_moved)
            costs = state.row_costs(col)
            min_cost = costs.min()
            best_rows = np.flatnonzero(costs == min_cost)

            # 2. Select value (with sideways move preference)
            cur_row = state.queens[col]
            other_best = best_rows[best_rows != cur_row]

            if other_best.size > 0:
                # Prefer moving to a DIFFERENT row with the same minimal conflicts
                new_row = int(rng.choice(other_best))
            elif rng.random() < 0.05:
                # Local minimum escape: pick any random row to break stagnation
                new_row = int(rng.integers(0, n))
            else:
                new_row = cur_row

            state.move(col, new_row)
            last_moved = col

        elapsed = time.perf_counter() - t0

        return MinConflictsResult(
            n, self.selector.name, seed, solved, steps, elapsed,
            Board.from_columns(state.queens), history
        )