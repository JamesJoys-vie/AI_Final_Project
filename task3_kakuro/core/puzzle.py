"""Kakuro board model and the text-file loader."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, NamedTuple, Optional

PUZZLES_DIR = Path(__file__).resolve().parent.parent / "puzzles"


class CellKind(Enum):
    BLOCK = "block"
    WHITE = "white"


class Cell(NamedTuple):
    """`down` = sum of the white run below this block, `right` = sum of the run to its right (None = no clue)."""

    row: int
    col: int
    kind: CellKind
    down: Optional[int] = None
    right: Optional[int] = None


class KakuroPuzzle:
    def __init__(self, name: str, grid: List[List[Cell]]):
        self.name = name
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])

    def cell(self, row: int, col: int) -> Cell:
        return self.grid[row][col]

    def is_white(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols and self.grid[row][col].kind is CellKind.WHITE

    def white_cells(self) -> List[tuple]:
        return [(c.row, c.col) for line in self.grid for c in line if c.kind is CellKind.WHITE]


class PuzzleLoader:
    """Token format per cell: 'X' block, '.' white, 'D\\R' clue (e.g. '14\\12', '21\\', '\\16')."""

    @staticmethod
    def available() -> List[str]:
        return sorted(path.stem for path in PUZZLES_DIR.glob("*.txt"))

    @classmethod
    def load(cls, name_or_path: str) -> KakuroPuzzle:
        path = Path(name_or_path)
        if not path.exists():
            path = PUZZLES_DIR / f"{name_or_path}.txt"
        return cls.parse(path.read_text(encoding="utf-8"), path.stem)

    @staticmethod
    def parse(text: str, name: str = "puzzle") -> KakuroPuzzle:
        grid: List[List[Cell]] = []
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith(";"):
                continue
            row_index = len(grid)
            row: List[Cell] = []
            for col_index, token in enumerate(line.split()):
                if token == ".":
                    row.append(Cell(row_index, col_index, CellKind.WHITE))
                elif token.upper() in ("X", "#"):
                    row.append(Cell(row_index, col_index, CellKind.BLOCK))
                elif "\\" in token:
                    down, right = token.split("\\", 1)
                    row.append(Cell(row_index, col_index, CellKind.BLOCK,
                                    int(down) if down else None, int(right) if right else None))
                else:
                    raise ValueError(f"Bad token '{token}' at row {row_index}, col {col_index}")
            grid.append(row)
        if not grid or any(len(r) != len(grid[0]) for r in grid):
            raise ValueError("Kakuro grid must be a non-empty rectangle")
        return KakuroPuzzle(name, grid)
