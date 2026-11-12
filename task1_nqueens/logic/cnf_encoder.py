"""
Builds the CNF formula of N-Queens.
Step 1 - discover constraints: group squares that attack each other into "lines"
         (rows, columns, diagonals r-c = k, anti-diagonals r+c = k).
Step 2 - convert to CNF:
         * at least one queen per row:  (Q(r,0) v Q(r,1) v ... v Q(r,N-1))
         * at most one queen per line, with one of two encodings:
             - pairwise: for every pair a, b in a line:  ~(Qa ^ Qb)  ==  (~Qa v ~Qb)  (De Morgan)
                         k(k-1)/2 clauses per line of k squares, no extra variables  -> O(N^3) clauses
             - seqcounter (Sinz 2005, sequential counter): auxiliary variables s_1..s_{k-1}, where
                         s_i means "a queen stands on one of the first i squares of the line":
                           (~x_1 v s_1)
                           (~x_i v s_i), (~s_{i-1} v s_i), (~x_i v ~s_{i-1})    for 1 < i < k
                           (~x_k v ~s_{k-1})
                         3k-4 clauses and k-1 variables per line                 -> O(N^2) clauses
                         It is only used where it is smaller than pairwise (k >= 6).
         * optional (column_alo): at least one queen per column. Redundant (N queens, one per row,
           at most one per column already imply it) but gives the solver more unit propagation.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Dict, List, NamedTuple, Tuple

from task1_nqueens.logic.variable_mapper import VariableMapper

Clause = List[int]
AMO_ENCODINGS = ("pairwise", "seqcounter")
SEQCOUNTER_MIN_LENGTH = 6  # 3k-4 < k(k-1)/2  <=>  k >= 6


class ConstraintLine(NamedTuple):
    kind: str
    key: int
    cells: Tuple[Tuple[int, int], ...]


class CnfFormula(NamedTuple):
    clauses: List[Clause]
    variable_count: int
    clauses_by_kind: Dict[str, int]


def amo_clause_count(length: int, amo: str) -> int:
    """Clauses needed to say "at most one of `length` literals" with the given encoding."""
    if length < 2:
        return 0
    pairwise = length * (length - 1) // 2
    if amo == "seqcounter" and length >= SEQCOUNTER_MIN_LENGTH:
        return 3 * length - 4
    return pairwise


class NQueensCnfEncoder:
    def __init__(self, n: int, amo: str = "pairwise", column_alo: bool = False):
        if amo not in AMO_ENCODINGS:
            raise ValueError(f"Unknown at-most-one encoding '{amo}', expected one of {AMO_ENCODINGS}")
        self.n = n
        self.amo = amo
        self.column_alo = column_alo
        self.mapper = VariableMapper(n)

    @property
    def label(self) -> str:
        return self.amo + (" + column ALO" if self.column_alo else "")

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
        n = self.n
        clauses: List[Clause] = []
        counts: Dict[str, int] = defaultdict(int)
        next_var = n * n + 1  # auxiliary variables (sequential counter) come after the N^2 square variables

        # Variable ids are computed inline (r * N + c + 1, see VariableMapper) instead of one call per literal.
        clauses.extend([row * n + col + 1 for col in range(n)] for row in range(n))
        counts["at-least-one (row)"] = n
        if self.column_alo:
            clauses.extend([row * n + col + 1 for row in range(n)] for col in range(n))
            counts["at-least-one (column)"] = n

        for line in self.discover_lines():
            literals = [row * n + col + 1 for row, col in line.cells]
            before = len(clauses)
            if self.amo == "seqcounter" and len(literals) >= SEQCOUNTER_MIN_LENGTH:
                next_var = self._sequential_counter(literals, next_var, clauses)
            else:
                negated = [-x for x in literals]
                clauses.extend(map(list, combinations(negated, 2)))
            counts[f"at-most-one ({line.kind})"] += len(clauses) - before

        return CnfFormula(clauses, next_var - 1, dict(counts))

    @staticmethod
    def _sequential_counter(x: List[int], next_var: int, clauses: List[Clause]) -> int:
        """Appends the Sinz sequential-counter clauses for AMO(x); returns the next free variable id."""
        k = len(x)
        s = list(range(next_var, next_var + k - 1))  # s[i] <=> some x[0..i] is true
        clauses.append([-x[0], s[0]])
        for i in range(1, k - 1):
            clauses.append([-x[i], s[i]])
            clauses.append([-s[i - 1], s[i]])
            clauses.append([-x[i], -s[i - 1]])
        clauses.append([-x[k - 1], -s[k - 2]])
        return next_var + k - 1

    def clause_count(self) -> int:
        """Clause count predicted from the line lengths alone (used to double-check `encode`)."""
        n = self.n
        lengths = [n] * (2 * n)  # rows and columns
        for length in list(range(1, n)) + [n] + list(range(n - 1, 0, -1)):
            lengths += [length, length]  # one diagonal and one anti-diagonal of each length
        total = n + (n if self.column_alo else 0)
        return total + sum(amo_clause_count(length, self.amo) for length in lengths)

    @staticmethod
    def expected_clause_count(n: int) -> int:
        """
        Closed form of the pairwise encoding (no column ALO):
        N (rows) + N^2 (N-1) (row + column pairs) + N (N-1) (2N-1) / 3 (both diagonal directions).
        """
        return n + n * n * (n - 1) + n * (n - 1) * (2 * n - 1) // 3
