"""
Min-Conflicts local search (Lecture 08) on the CSP form of N-Queens:
one variable per row, value = column, so row conflicts are impossible by construction.
"""
from __future__ import annotations

import random
import time
from typing import Iterator, List, NamedTuple, Optional

from task1_nqueens.solvers.solve_result import SolveResult
from task1_nqueens.solvers.variable_selectors import RandomConflictedSelector, VariableSelector


class ConflictBoard:
    """Keeps queen counters per column / diagonal / anti-diagonal, so conflicts(row, col) is O(1)."""

    def __init__(self, columns: List[int]):
        self.n = len(columns)
        self.columns = list(columns)
        self.col_count = [0] * self.n
        self.diag_count = [0] * (2 * self.n - 1)
        self.anti_count = [0] * (2 * self.n - 1)
        for row, col in enumerate(self.columns):
            self._update(row, col, +1)

    def _update(self, row: int, col: int, delta: int) -> None:
        self.col_count[col] += delta
        self.diag_count[row - col + self.n - 1] += delta
        self.anti_count[row + col] += delta

    def conflicts(self, row: int, col: int) -> int:
        """Number of OTHER queens attacking square (row, col)."""
        count = self.col_count[col] + self.diag_count[row - col + self.n - 1] + self.anti_count[row + col]
        return count - 3 if self.columns[row] == col else count

    def move(self, row: int, col: int) -> None:
        self._update(row, self.columns[row], -1)
        self.columns[row] = col
        self._update(row, col, +1)

    def conflicted_rows(self) -> List[tuple]:
        return [(row, c) for row in range(self.n) if (c := self.conflicts(row, self.columns[row])) > 0]

    def attacking_pairs(self) -> int:
        lines = self.col_count + self.diag_count + self.anti_count
        return sum(k * (k - 1) // 2 for k in lines)


class MinConflictsStep(NamedTuple):
    step: int
    row: int
    old_col: int
    new_col: int
    attacking_pairs: int


class MinConflictsSolver:
    """
    MIN-CONFLICTS(csp, max_steps): start from a complete random assignment, then repeatedly
    pick a conflicted variable (strategy) and give it the value with the fewest conflicts.
    """

    def __init__(self, selector: Optional[VariableSelector] = None, max_steps_factor: int = 50,
                 seed: Optional[int] = None):
        self.selector = selector or RandomConflictedSelector()
        self.max_steps_factor = max_steps_factor
        self.seed = seed

    @property
    def name(self) -> str:
        return f"Min-Conflicts {self.selector.name}"

    def iter_steps(self, n: int, rng: Optional[random.Random] = None) -> Iterator[MinConflictsStep]:
        """Generator version (one yield per repair) used by the GUI animation and by solve()."""
        rng = rng or random.Random(self.seed)
        self.board = ConflictBoard([rng.randrange(n) for _ in range(n)])
        self.selector.reset(n)
        for step in range(1, self.max_steps_factor * n + 1):
            conflicted = self.board.conflicted_rows()
            if not conflicted:
                return
            row = self.selector.select(conflicted, rng)
            costs = [self.board.conflicts(row, col) for col in range(n)]
            best = min(costs)
            new_col = rng.choice([col for col, cost in enumerate(costs) if cost == best])
            old_col = self.board.columns[row]
            self.board.move(row, new_col)
            self.selector.notify_moved(row)
            yield MinConflictsStep(step, row, old_col, new_col, self.board.attacking_pairs())

    def solve(self, n: int) -> SolveResult:
        start = time.perf_counter()
        steps = 0
        for steps, _ in enumerate(self.iter_steps(n), 1):
            pass
        elapsed = time.perf_counter() - start
        solved = self.board.attacking_pairs() == 0
        return SolveResult(self.name, n, solved, list(self.board.columns), elapsed, steps)
