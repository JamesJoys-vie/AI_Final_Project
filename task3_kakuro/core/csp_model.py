"""
Kakuro as a CSP (X, D, C):
X = every white cell,  D = {1..9} for each cell,
C = one n-ary RunConstraint per clue: cells of the run are ALL DIFFERENT and their SUM equals the clue.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Mapping, Optional, Tuple

from task3_kakuro.core.puzzle import KakuroPuzzle

Variable = Tuple[int, int]
DIGITS: FrozenSet[int] = frozenset(range(1, 10))


class RunConstraint:
    def __init__(self, index: int, cells: Tuple[Variable, ...], total: int, direction: str, clue: Variable):
        self.index = index
        self.cells = cells
        self.total = total
        self.direction = direction
        self.clue = clue

    def __repr__(self) -> str:
        return f"{self.direction} run at {self.clue}: sum {self.total} over {len(self.cells)} cells"

    def is_consistent(self, assignment: Mapping[Variable, int]) -> bool:
        """
        Check a PARTIAL assignment: no repeated digit, and the remaining cells can still reach the sum
        (smallest / largest sums of the unused digits bound what is reachable).
        """
        values = [assignment[c] for c in self.cells if c in assignment]
        if len(values) != len(set(values)):
            return False
        remaining = len(self.cells) - len(values)
        need = self.total - sum(values)
        if remaining == 0:
            return need == 0
        unused = sorted(DIGITS - set(values))
        return sum(unused[:remaining]) <= need <= sum(unused[-remaining:])


class KakuroCSP:
    def __init__(self, puzzle: KakuroPuzzle):
        self.puzzle = puzzle
        self.variables: List[Variable] = puzzle.white_cells()
        self.domains: Dict[Variable, FrozenSet[int]] = {v: DIGITS for v in self.variables}
        self.constraints: List[RunConstraint] = self._build_constraints()
        self.constraints_of: Dict[Variable, List[RunConstraint]] = {v: [] for v in self.variables}
        for constraint in self.constraints:
            for cell in constraint.cells:
                self.constraints_of[cell].append(constraint)
        self.neighbors: Dict[Variable, set] = {
            v: {c for con in self.constraints_of[v] for c in con.cells if c != v} for v in self.variables}

    def _build_constraints(self) -> List[RunConstraint]:
        """For every clue, walk right (across) or down while cells are white to collect its run."""
        constraints = []
        p = self.puzzle
        for line in p.grid:
            for cell in line:
                for total, (dr, dc), direction in ((cell.right, (0, 1), "across"), (cell.down, (1, 0), "down")):
                    if total is None:
                        continue
                    run, r, c = [], cell.row + dr, cell.col + dc
                    while p.is_white(r, c):
                        run.append((r, c))
                        r, c = r + dr, c + dc
                    if run:
                        constraints.append(RunConstraint(len(constraints), tuple(run), total, direction,
                                                         (cell.row, cell.col)))
        return constraints

    def is_solution(self, assignment: Optional[Mapping[Variable, int]]) -> bool:
        if assignment is None or any(v not in assignment for v in self.variables):
            return False
        return all(c.is_consistent(assignment) for c in self.constraints)

    def uncovered_cells(self) -> List[Variable]:
        """White cells that belong to no run (badly formed puzzle)."""
        return [v for v in self.variables if not self.constraints_of[v]]
