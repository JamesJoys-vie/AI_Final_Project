"""
Min-Conflicts local search (Lecture 08) on the CSP form of N-Queens:
one variable per row, value = column, so row conflicts are impossible by construction.
"""
from __future__ import annotations

import random
import time
from bisect import bisect_left, insort
from typing import Callable, Dict, Iterator, List, NamedTuple, Optional, Set

from task1_nqueens.solvers.solve_result import SolveResult
from task1_nqueens.solvers.variable_selectors import RandomConflictedSelector, VariableSelector


class ConflictBoard:
    """
    Incremental state of a complete assignment (one queen per row).

    Per line (column / diagonal / anti-diagonal) it keeps the queen count and the set of rows on it,
    so a move only touches the rows sharing one of the 6 lines involved (old and new square) instead
    of rescanning the whole board. Maintained incrementally after every move:
      * `row_conflicts[r]` - number of other queens attacking the queen of row r,
      * `conflicted`       - rows with row_conflicts > 0, kept sorted (deterministic random choice),
      * `buckets`          - conflict count -> set of rows with that count (fast "most conflicted"),
      * `pairs`            - total number of attacking pairs.
    """

    def __init__(self, columns: List[int]):
        n = self.n = len(columns)
        self.columns = list(columns)
        self.col_count = [0] * n
        self.diag_count = [0] * (2 * n - 1)
        self.anti_count = [0] * (2 * n - 1)
        self.col_rows: List[Set[int]] = [set() for _ in range(n)]
        self.diag_rows: List[Set[int]] = [set() for _ in range(2 * n - 1)]
        self.anti_rows: List[Set[int]] = [set() for _ in range(2 * n - 1)]
        self.pairs = 0
        for row, col in enumerate(self.columns):
            self._add(row, col)

        self.row_conflicts = [self.conflicts(row, col) for row, col in enumerate(self.columns)]
        self.conflicted: List[int] = [row for row in range(n) if self.row_conflicts[row] > 0]
        self.buckets: Dict[int, Set[int]] = {}
        for row in self.conflicted:
            self.buckets.setdefault(self.row_conflicts[row], set()).add(row)

    # ----------------------------------------------------------------- line counters
    def _add(self, row: int, col: int) -> None:
        d, a = row - col + self.n - 1, row + col
        self.pairs += self.col_count[col] + self.diag_count[d] + self.anti_count[a]
        self.col_count[col] += 1
        self.diag_count[d] += 1
        self.anti_count[a] += 1
        self.col_rows[col].add(row)
        self.diag_rows[d].add(row)
        self.anti_rows[a].add(row)

    def _remove(self, row: int, col: int) -> None:
        d, a = row - col + self.n - 1, row + col
        self.col_count[col] -= 1
        self.diag_count[d] -= 1
        self.anti_count[a] -= 1
        self.pairs -= self.col_count[col] + self.diag_count[d] + self.anti_count[a]
        self.col_rows[col].discard(row)
        self.diag_rows[d].discard(row)
        self.anti_rows[a].discard(row)

    def _rows_on_lines(self, row: int, col: int) -> List[int]:
        """Rows (other than `row`) whose queen shares a line with square (row, col).
        Two distinct squares share at most one line, so no row is listed twice."""
        d, a = row - col + self.n - 1, row + col
        return [r for line in (self.col_rows[col], self.diag_rows[d], self.anti_rows[a]) for r in line if r != row]

    # ----------------------------------------------------------------- per-row conflicts
    def _set_row_conflicts(self, row: int, value: int) -> None:
        old = self.row_conflicts[row]
        if old == value:
            return
        self.row_conflicts[row] = value
        if old > 0:
            bucket = self.buckets[old]
            bucket.discard(row)
            if not bucket:
                del self.buckets[old]
        else:
            insort(self.conflicted, row)
        if value > 0:
            self.buckets.setdefault(value, set()).add(row)
        else:
            del self.conflicted[bisect_left(self.conflicted, row)]

    # ----------------------------------------------------------------- public API
    def conflicts(self, row: int, col: int) -> int:
        """Number of OTHER queens attacking square (row, col)."""
        count = self.col_count[col] + self.diag_count[row - col + self.n - 1] + self.anti_count[row + col]
        return count - 3 if self.columns[row] == col else count

    def column_costs(self, row: int) -> List[int]:
        """conflicts(row, col) for every column, computed with list slices instead of N method calls."""
        n = self.n
        diag = self.diag_count[row:row + n]
        diag.reverse()  # diag index of column c is row - c + n - 1, i.e. descending in c
        costs = [c + d + a for c, d, a in zip(self.col_count, diag, self.anti_count[row:row + n])]
        costs[self.columns[row]] -= 3
        return costs

    def move(self, row: int, col: int) -> None:
        old_col = self.columns[row]
        if old_col == col:
            return
        for other in self._rows_on_lines(row, old_col):
            self._set_row_conflicts(other, self.row_conflicts[other] - 1)
        self._remove(row, old_col)
        self.columns[row] = col
        self._add(row, col)
        for other in self._rows_on_lines(row, col):
            self._set_row_conflicts(other, self.row_conflicts[other] + 1)
        self._set_row_conflicts(row, self.conflicts(row, col))

    def conflicted_rows(self) -> List[tuple]:
        """(row, conflicts) for every conflicted row, ascending by row."""
        return [(row, self.row_conflicts[row]) for row in self.conflicted]

    def attacking_pairs(self) -> int:
        return self.pairs


class MinConflictsStep(NamedTuple):
    step: int
    row: int
    old_col: int
    new_col: int
    attacking_pairs: int
    restart: int = 0


def random_columns(n: int, rng: random.Random) -> List[int]:
    """Complete random assignment: every row gets an independent uniformly random column."""
    return [rng.randrange(n) for _ in range(n)]


def greedy_columns(n: int, rng: random.Random, tries: int = 20) -> List[int]:
    """
    Greedy initial assignment (in the spirit of Minton et al. 1992 / Sosic & Gu 1991), O(N) expected.
    Columns are drawn without replacement, so the result is a permutation (no column conflicts).
    For each row we try up to `tries` random unused columns and keep the first one that no placed
    queen attacks diagonally; if none is found, a random unused column is accepted. Only the last
    few rows usually end up conflicted, so the repair phase starts close to a solution.
    """
    free = list(range(n))
    diag = [False] * (2 * n - 1)
    anti = [False] * (2 * n - 1)
    columns = [0] * n
    randrange = rng.randrange
    for row in range(n):
        remaining = n - row
        index = randrange(remaining)
        for _ in range(min(tries, remaining)):
            col = free[index]
            if not diag[row - col + n - 1] and not anti[row + col]:
                break
            index = randrange(remaining)
        col = free[index]
        free[index] = free[remaining - 1]  # O(1) removal from the unused pool
        free.pop()
        columns[row] = col
        diag[row - col + n - 1] = True
        anti[row + col] = True
    return columns


INITIALIZERS: Dict[str, Callable[[int, random.Random], List[int]]] = {
    "random": random_columns,
    "greedy": greedy_columns,
}


class MinConflictsSolver:
    """
    MIN-CONFLICTS(csp, max_steps): start from a complete assignment, then repeatedly
    pick a conflicted variable (strategy) and give it the value with the fewest conflicts.
    `init` chooses the starting assignment: "random" (textbook) or "greedy" (see greedy_columns).
    If max_steps (= max_steps_factor * N) repairs do not reach a solution, restart from a new
    initial assignment, at most `max_restarts` times.
    """

    def __init__(self, selector: Optional[VariableSelector] = None, max_steps_factor: int = 50,
                 seed: Optional[int] = None, max_restarts: int = 10, init: str = "random"):
        if init not in INITIALIZERS:
            raise ValueError(f"Unknown init '{init}', expected one of {sorted(INITIALIZERS)}")
        self.selector = selector or RandomConflictedSelector()
        self.max_steps_factor = max_steps_factor
        self.max_restarts = max_restarts
        self.seed = seed
        self.init = init
        self.restarts = 0
        self.initial_pairs = 0

    @property
    def name(self) -> str:
        suffix = "" if self.init == "random" else f" [{self.init} init]"
        return f"Min-Conflicts {self.selector.name}{suffix}"

    def iter_steps(self, n: int, rng: Optional[random.Random] = None) -> Iterator[MinConflictsStep]:
        """Generator version (one yield per repair) used by the GUI animation and by solve()."""
        rng = rng or random.Random(self.seed)
        choice = rng.choice
        initializer = INITIALIZERS[self.init]
        step = 0
        for attempt in range(self.max_restarts + 1):
            self.restarts = attempt
            self.board = board = ConflictBoard(initializer(n, rng))
            if attempt == 0:
                self.initial_pairs = board.pairs
            self.selector.reset(n)
            for _ in range(self.max_steps_factor * n):
                if not board.conflicted:
                    return
                row = self.selector.select(board, rng)
                costs = board.column_costs(row)
                best = min(costs)
                new_col = choice([col for col, cost in enumerate(costs) if cost == best])
                old_col = board.columns[row]
                board.move(row, new_col)
                self.selector.notify_moved(row)
                step += 1
                yield MinConflictsStep(step, row, old_col, new_col, board.pairs, attempt)
            if not board.conflicted:
                return

    def solve(self, n: int) -> SolveResult:
        start = time.perf_counter()
        steps = 0
        for steps, _ in enumerate(self.iter_steps(n), 1):
            pass
        elapsed = time.perf_counter() - start
        solved = self.board.pairs == 0
        return SolveResult(self.name, n, solved, list(self.board.columns), elapsed, steps,
                           extra={"initial_pairs": self.initial_pairs}, restarts=self.restarts)
