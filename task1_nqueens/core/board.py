"""N x N board where the user (or a solver) places queens; counts attacking pairs."""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

Cell = Tuple[int, int]
LineKey = Tuple[int, int]  # (line kind 0..3, index) - row, column, diagonal r-c, anti-diagonal r+c


def attacks(a: Cell, b: Cell) -> bool:
    """Two queens attack each other on the same row, column or diagonal."""
    return a[0] == b[0] or a[1] == b[1] or abs(a[0] - b[0]) == abs(a[1] - b[1])


def _lines(row: int, col: int) -> Tuple[LineKey, LineKey, LineKey, LineKey]:
    return (0, row), (1, col), (2, row - col), (3, row + col)


class QueenBoard:
    """
    Any set of queens (several per row allowed, as the user clicks freely).
    Each line (row / column / diagonal / anti-diagonal) keeps the set of queens on it, updated on every
    add / remove, together with the running number of attacking pairs. So:
      * pair count and is_solution() are O(1),
      * attacking_pairs() only looks inside lines holding 2+ queens (two distinct squares share at most
        one line, so each pair is found exactly once) and is cached until the board changes,
      * attacked_cells() is O(N^2) instead of O(N^2 * queens).
    `queens` is read-only for callers: change the board through toggle / add / remove / clear.
    """

    def __init__(self, n: int):
        self.n = n
        self._queens: Set[Cell] = set()
        self._lines: Dict[LineKey, Set[Cell]] = {}
        self._pair_count = 0
        self._pairs_cache: Optional[List[Tuple[Cell, Cell]]] = None

    @classmethod
    def from_columns(cls, columns: List[int]) -> "QueenBoard":
        """columns[row] = column of the queen in that row (solver output format)."""
        board = cls(len(columns))
        for row, col in enumerate(columns):
            if col is not None and col >= 0:
                board.add(row, col)
        return board

    # ----------------------------------------------------------------- editing
    @property
    def queens(self) -> FrozenSet[Cell]:
        return frozenset(self._queens)

    def add(self, row: int, col: int) -> None:
        cell = (row, col)
        if cell in self._queens:
            return
        self._queens.add(cell)
        for key in _lines(row, col):
            line = self._lines.setdefault(key, set())
            self._pair_count += len(line)
            line.add(cell)
        self._pairs_cache = None

    def remove(self, row: int, col: int) -> None:
        cell = (row, col)
        if cell not in self._queens:
            return
        self._queens.remove(cell)
        for key in _lines(row, col):
            line = self._lines[key]
            line.remove(cell)
            self._pair_count -= len(line)
            if not line:
                del self._lines[key]
        self._pairs_cache = None

    def toggle(self, row: int, col: int) -> None:
        if (row, col) in self._queens:
            self.remove(row, col)
        else:
            self.add(row, col)

    def clear(self) -> None:
        self._queens.clear()
        self._lines.clear()
        self._pair_count = 0
        self._pairs_cache = None

    # ----------------------------------------------------------------- queries
    def attacking_pair_count(self) -> int:
        return self._pair_count

    def attacking_pairs(self) -> List[Tuple[Cell, Cell]]:
        """Every attacking pair (a, b) with a < b, sorted."""
        if self._pairs_cache is None:
            pairs = []
            for line in self._lines.values():
                if len(line) > 1:
                    cells = sorted(line)
                    pairs.extend((a, b) for i, a in enumerate(cells) for b in cells[i + 1:])
            pairs.sort()
            self._pairs_cache = pairs
        return list(self._pairs_cache)

    def attacked_cells(self) -> Set[Cell]:
        """Squares attacked by at least one queen other than a queen standing on the square itself."""
        def queens_on(key: LineKey) -> int:
            line = self._lines.get(key)
            return len(line) if line else 0

        result = set()
        for r in range(self.n):
            for c in range(self.n):
                own = 4 if (r, c) in self._queens else 0  # a queen sits on all 4 of its own lines
                if sum(queens_on(key) for key in _lines(r, c)) > own:
                    result.add((r, c))
        return result

    def is_solution(self) -> bool:
        return len(self._queens) == self.n and self._pair_count == 0

    def as_columns(self) -> List[Optional[int]]:
        columns: List[Optional[int]] = [None] * self.n
        for row, col in self._queens:
            columns[row] = col
        return columns


def is_valid_solution(columns: Optional[Iterable[Optional[int]]]) -> bool:
    """
    Independent O(N) checker used by the experiments to verify every solver output:
    one queen per row (by construction of the list), every column inside the board,
    and all columns, diagonals (r - c) and anti-diagonals (r + c) distinct.
    """
    if columns is None:
        return False
    columns = list(columns)
    n = len(columns)
    if any(not isinstance(col, int) or not 0 <= col < n for col in columns):
        return False
    return (len(set(columns)) == n
            and len({row - col for row, col in enumerate(columns)}) == n
            and len({row + col for row, col in enumerate(columns)}) == n)
