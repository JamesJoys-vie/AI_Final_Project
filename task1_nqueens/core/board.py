"""N x N board where the user (or a solver) places queens; counts attacking pairs."""
from __future__ import annotations

from itertools import combinations
from typing import Iterable, List, Optional, Set, Tuple

Cell = Tuple[int, int]


def attacks(a: Cell, b: Cell) -> bool:
    """Two queens attack each other on the same row, column or diagonal."""
    return a[0] == b[0] or a[1] == b[1] or abs(a[0] - b[0]) == abs(a[1] - b[1])


class QueenBoard:
    def __init__(self, n: int):
        self.n = n
        self.queens: Set[Cell] = set()

    @classmethod
    def from_columns(cls, columns: List[int]) -> "QueenBoard":
        """columns[row] = column of the queen in that row (solver output format)."""
        board = cls(len(columns))
        board.queens = {(row, col) for row, col in enumerate(columns) if col is not None and col >= 0}
        return board

    def toggle(self, row: int, col: int) -> None:
        cell = (row, col)
        if cell in self.queens:
            self.queens.remove(cell)
        else:
            self.queens.add(cell)

    def clear(self) -> None:
        self.queens.clear()

    def attacking_pairs(self) -> List[Tuple[Cell, Cell]]:
        return [(a, b) for a, b in combinations(sorted(self.queens), 2) if attacks(a, b)]

    def attacked_cells(self) -> Set[Cell]:
        return {(r, c) for r in range(self.n) for c in range(self.n)
                if any(attacks((r, c), q) for q in self.queens if q != (r, c))}

    def is_solution(self) -> bool:
        return len(self.queens) == self.n and not self.attacking_pairs()

    def as_columns(self) -> List[Optional[int]]:
        columns: List[Optional[int]] = [None] * self.n
        for row, col in self.queens:
            columns[row] = col
        return columns


def is_valid_solution(columns: Iterable[int]) -> bool:
    """Independent checker used by the experiments to verify every solver output."""
    columns = list(columns)
    return QueenBoard.from_columns(columns).is_solution()
