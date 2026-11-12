"""
Builds the CNF formula of N-Queens.
Step 1 - discover constraints: group squares that attack each other into "lines"
         (rows, columns, diagonals r-c = k, anti-diagonals r+c = k).
Step 2 - convert to CNF:
         * at least one queen per row:  (Q(r,0) v Q(r,1) v ... v Q(r,N-1))
         * at most one queen per line:  for every pair a, b in a line:  ~(Qa ^ Qb)  ==  (~Qa v ~Qb)  (De Morgan)
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Dict, List, NamedTuple, Tuple

from task1_nqueens.logic.variable_mapper import VariableMapper

Clause = List[int]


class ConstraintLine(NamedTuple):
    kind: str
    key: int
    cells: Tuple[Tuple[int, int], ...]


class CnfFormula(NamedTuple):
    clauses: List[Clause]
    variable_count: int
    clauses_by_kind: Dict[str, int]


class NQueensCnfEncoder:
    def __init__(self, n: int):
        self.n = n
        self.mapper = VariableMapper(n)

    def discover_lines(self) -> List[ConstraintLine]:
        """
        One pass over all N^2 squares; each square is added to the 4 lines it belongs to.
        Lines with a single square (corners of diagonals) give no constraint and are dropped.
        """
        groups: Dict[Tuple[str, int], List[Tuple[int, int]]] = defaultdict(list)
        for row in range(self.n):
            for col in range(self.n):
                groups[("row", row)].append((row, col))
                groups[("column", col)].append((row, col))
                groups[("diagonal", row - col)].append((row, col))
                groups[("anti-diagonal", row + col)].append((row, col))
        return [ConstraintLine(kind, key, tuple(cells)) for (kind, key), cells in groups.items() if len(cells) > 1]

    def encode(self) -> CnfFormula:
        clauses: List[Clause] = []
        counts: Dict[str, int] = defaultdict(int)
        to_var = self.mapper.to_variable

        for row in range(self.n):
            clauses.append([to_var(row, col) for col in range(self.n)])
            counts["at-least-one (row)"] += 1

        for line in self.discover_lines():
            for (r1, c1), (r2, c2) in combinations(line.cells, 2):
                clauses.append([-to_var(r1, c1), -to_var(r2, c2)])
                counts[f"at-most-one ({line.kind})"] += 1

        return CnfFormula(clauses, self.mapper.variable_count, dict(counts))

    @staticmethod
    def expected_clause_count(n: int) -> int:
        """
        Closed form used to double-check the encoder:
        N (rows) + N^2 (N-1) (row + column pairs) + N (N-1) (2N-1) / 3 (both diagonal directions).
        """
        return n + n * n * (n - 1) + n * (n - 1) * (2 * n - 1) // 3
