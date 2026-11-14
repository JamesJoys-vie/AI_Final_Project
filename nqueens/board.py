"""Board model: a pure data class used by every solver to represent / verify a result."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Sequence, Tuple

Cell = Tuple[int, int]  # (row, col), 0-indexed


class Board:
    """An N x N chess board holding a set of queens."""

    def __init__(self, n: int, queens: Iterable[Cell] = ()):
        if n < 1:
            raise ValueError("Board size N must be >= 1")
        self.n = n
        self.queens: List[Cell] = sorted(set(queens))
        for r, c in self.queens:
            if not (0 <= r < n and 0 <= c < n):
                raise ValueError(f"Queen {(r, c)} is outside the {n}x{n} board")

    @classmethod
    def from_columns(cls, rows_by_col: Sequence[int]) -> "Board":
        """Build from the CSP representation: queen of column c sits on row rows_by_col[c]."""
        return cls(len(rows_by_col), [(int(r), c) for c, r in enumerate(rows_by_col)])

    def count_attacking_pairs(self) -> int:
        """O(N): queens attack each other iff they share a row, column or diagonal."""
        keys = (
            lambda q: q[0],         # row
            lambda q: q[1],         # column
            lambda q: q[0] - q[1],  # main diagonal  (r - c constant)
            lambda q: q[0] + q[1],  # anti diagonal  (r + c constant)
        )
        pairs = 0
        for key in keys:
            pairs += sum(k * (k - 1) // 2 for k in Counter(map(key, self.queens)).values())
        return pairs

    def is_valid_solution(self) -> bool:
        return len(self.queens) == self.n and self.count_attacking_pairs() == 0

    def render(self, queen: str = "Q", empty: str = ".") -> str:
        grid = [[empty] * self.n for _ in range(self.n)]
        for r, c in self.queens:
            grid[r][c] = queen
        return "\n".join(" ".join(row) for row in grid)

    def __repr__(self) -> str:
        return f"Board(n={self.n}, queens={len(self.queens)})"
