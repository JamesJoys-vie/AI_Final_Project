"""Maps each square (row, col) to a propositional variable number for the SAT solver."""
from __future__ import annotations

from typing import Tuple


class VariableMapper:
    """
    Q(r, c) is True  <=>  a queen stands on square (r, c).  Variable id = r * N + c + 1 (DIMACS ids start at 1).
    """

    def __init__(self, n: int):
        self.n = n

    @property
    def variable_count(self) -> int:
        return self.n * self.n

    def to_variable(self, row: int, col: int) -> int:
        return row * self.n + col + 1

    def to_cell(self, variable: int) -> Tuple[int, int]:
        index = abs(variable) - 1
        return index // self.n, index % self.n

    def name(self, literal: int) -> str:
        row, col = self.to_cell(literal)
        return f"{'~' if literal < 0 else ''}Q{row},{col}"
